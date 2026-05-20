"""iNat enrichment service — bir tur uchun rasm va meta ma'lumotlarini boyitadi."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import httpx
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import _get_sessionmaker
from app.models.species import Species
from app.models.species_photo import SpeciesPhoto

log = logging.getLogger(__name__)

INAT_BASE = "https://api.inaturalist.org/v1"
UZ_PLACE_ID = 109842  # iNaturalist O'zbekiston place_id

# Pauza har bir tashqi so'rovdan keyin (rate-limit hurmat).
# iNat soft limit: 100 req/min = ~1.7/sec. 0.7s pauza = ~85 req/min, xavfsiz.
_POLITE_SLEEP_SEC = 0.7


@dataclass
class EnrichResult:
    species_id: int
    latin: str
    taxon_id: Optional[int]
    photos_added: int
    default_set: bool
    error: Optional[str] = None


async def _http_get(
    client: httpx.AsyncClient, url: str, params: dict | None = None
) -> dict | None:
    """GET with retry for transient errors (429, 5xx, network)."""
    for attempt in range(4):
        try:
            r = await client.get(url, params=params, timeout=15.0)
            if r.status_code == 200:
                return r.json()
            # Rate limit / server error — exponential backoff (1s, 4s, 13s)
            if r.status_code == 429 or r.status_code >= 500:
                if attempt < 3:
                    delay = (3 ** attempt) + 1.0
                    log.warning(
                        "iNat HTTP %s for %s, retry %d in %.1fs",
                        r.status_code, url, attempt + 1, delay,
                    )
                    await asyncio.sleep(delay)
                    continue
            log.warning("iNat HTTP %s for %s — giving up", r.status_code, url)
            return None
        except (httpx.RequestError, httpx.TimeoutException) as e:
            if attempt < 3:
                await asyncio.sleep(1.0 + attempt)
                continue
            log.warning("iNat network error for %s: %s", url, e)
            return None
    return None


async def _find_taxon_id(client: httpx.AsyncClient, latin: str) -> Optional[int]:
    """Latin nom bo'yicha iNat taxon_id'ni topadi."""
    data = await _http_get(
        client,
        f"{INAT_BASE}/taxa",
        params={"q": latin, "rank": "species", "per_page": 1},
    )
    if not data:
        return None
    results = data.get("results") or []
    if not results:
        return None
    tid = results[0].get("id")
    try:
        return int(tid) if tid is not None else None
    except (TypeError, ValueError):
        return None


async def _fetch_taxon_detail(
    client: httpx.AsyncClient, taxon_id: int
) -> Optional[dict]:
    """Taxon detail (taxon_photos bilan)."""
    data = await _http_get(
        client, f"{INAT_BASE}/taxa/{taxon_id}", params={"locale": "uz"}
    )
    if not data:
        return None
    results = data.get("results") or []
    if not results:
        return None
    return results[0]


async def _enrich_one(
    species: Species,
    db: AsyncSession,
    client: httpx.AsyncClient,
    *,
    replace: bool = False,
) -> EnrichResult:
    """Bitta tur uchun enrichment (httpx client reuse uchun ichki helper)."""
    latin = (species.latin or "").strip()
    if not latin:
        return EnrichResult(
            species_id=species.id,
            latin="",
            taxon_id=None,
            photos_added=0,
            default_set=False,
            error="no latin name",
        )

    # 1) taxon_id ni topish
    taxon_id = await _find_taxon_id(client, latin)
    await asyncio.sleep(_POLITE_SLEEP_SEC)
    if taxon_id is None:
        return EnrichResult(
            species_id=species.id,
            latin=latin,
            taxon_id=None,
            photos_added=0,
            default_set=False,
            error="taxon not found",
        )

    # 2) Detail (taxon_photos)
    taxon = await _fetch_taxon_detail(client, taxon_id)
    await asyncio.sleep(_POLITE_SLEEP_SEC)
    if not taxon:
        return EnrichResult(
            species_id=species.id,
            latin=latin,
            taxon_id=taxon_id,
            photos_added=0,
            default_set=False,
            error="taxon detail empty",
        )

    photos = taxon.get("taxon_photos") or []
    if not photos:
        return EnrichResult(
            species_id=species.id,
            latin=latin,
            taxon_id=taxon_id,
            photos_added=0,
            default_set=False,
            error="no photos",
        )

    # 3) replace=True bo'lsa eski rasmlarni o'chiramiz
    if replace:
        await db.execute(
            delete(SpeciesPhoto).where(SpeciesPhoto.species_id == species.id)
        )

    # 4) Mavjud external_id'larni olib qo'yamiz (replace=False holatda dublikat oldi)
    existing_ids: set[str] = set()
    if not replace:
        rows = (
            await db.scalars(
                select(SpeciesPhoto.external_id).where(
                    SpeciesPhoto.species_id == species.id
                )
            )
        ).all()
        existing_ids = {str(x) for x in rows if x}

    photos_added = 0
    default_set = False
    first_url: Optional[str] = None

    for idx, tp in enumerate(photos):
        photo = (tp or {}).get("photo") or {}
        pid = photo.get("id")
        if pid is None:
            continue
        ext_id = str(pid)
        url = photo.get("medium_url") or ""
        if not url:
            continue
        if ext_id in existing_ids:
            continue

        is_default = idx == 0
        sp = SpeciesPhoto(
            species_id=species.id,
            url=url,
            attribution=(photo.get("attribution") or "")[:300],
            license_code=(photo.get("license_code") or "")[:20],
            source="inat",
            external_id=ext_id,
            is_default=is_default,
            ordering=idx,
        )
        db.add(sp)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            # UNIQUE buzilsa — bu rasmni o'tkazib yuboramiz
            continue

        existing_ids.add(ext_id)
        photos_added += 1
        if is_default:
            default_set = True
            first_url = url
        elif first_url is None:
            first_url = url

    # 5) Species.image_url bo'sh bo'lsa — default URL bilan to'ldiramiz
    if first_url and not (species.image_url or "").strip():
        species.image_url = first_url[:600]
        db.add(species)

    # 6) Commit
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        return EnrichResult(
            species_id=species.id,
            latin=latin,
            taxon_id=taxon_id,
            photos_added=0,
            default_set=False,
            error=f"commit failed: {e.__class__.__name__}",
        )

    return EnrichResult(
        species_id=species.id,
        latin=latin,
        taxon_id=taxon_id,
        photos_added=photos_added,
        default_set=default_set,
    )


async def enrich_species(
    species: Species, db: AsyncSession, *, replace: bool = False
) -> EnrichResult:
    """Bitta tur uchun iNat'dan rasmlar va meta'larni olib keladi.

    - replace=True bo'lsa mavjud SpeciesPhoto'larni o'chiradi va qaytadan yaratadi.
    - replace=False (default) bo'lsa external_id bo'yicha dublikat tekshirib qo'shadi.
    - Birinchi rasmni is_default=True belgilaydi VA Species.image_url ga yozadi (agar bo'sh bo'lsa).
    """
    async with httpx.AsyncClient(timeout=12.0) as client:
        return await _enrich_one(species, db, client, replace=replace)


async def enrich_many(
    species_ids: list[int], db: AsyncSession, *, concurrency: int = 4
) -> list[EnrichResult]:
    """Bulk enrichment — har bir task o'z AsyncSession'iga ega.

    AsyncSession concurrent-safe emas — bitta sessiyani ko'p task'da
    ishlatish IllegalStateChangeError keltirib chiqaradi. Shuning uchun
    `_get_sessionmaker()` orqali har bir task uchun yangi sessiya ochamiz.
    `db` parametri faqat species ro'yxatini boshlang'ich olish uchun ishlatiladi.
    """
    if not species_ids:
        return []

    # Asosiy `db` sessiyasida species'larni topamiz (ID + latin uchun).
    rows = (
        await db.scalars(select(Species).where(Species.id.in_(species_ids)))
    ).all()
    by_id = {s.id: (s.id, s.latin or "") for s in rows}

    results: list[EnrichResult] = []
    sem = asyncio.Semaphore(max(1, concurrency))
    sm = _get_sessionmaker()

    async with httpx.AsyncClient(timeout=12.0) as client:

        async def _task(sid: int, latin: str) -> EnrichResult:
            async with sem:
                # Har bir task — yangi sessiya. Task ichida species'ni qaytadan yuklaymiz.
                async with sm() as task_db:
                    try:
                        sp = await task_db.scalar(
                            select(Species).where(Species.id == sid)
                        )
                        if sp is None:
                            return EnrichResult(
                                species_id=sid,
                                latin=latin,
                                taxon_id=None,
                                photos_added=0,
                                default_set=False,
                                error="species not found",
                            )
                        return await _enrich_one(
                            sp, task_db, client, replace=False
                        )
                    except Exception as e:  # noqa: BLE001
                        log.exception("enrich_many failed for species=%s", sid)
                        try:
                            await task_db.rollback()
                        except Exception:  # noqa: BLE001
                            pass
                        return EnrichResult(
                            species_id=sid,
                            latin=latin,
                            taxon_id=None,
                            photos_added=0,
                            default_set=False,
                            error=f"exception: {e.__class__.__name__}",
                        )

        tasks = []
        for sid in species_ids:
            entry = by_id.get(sid)
            if entry is None:
                results.append(
                    EnrichResult(
                        species_id=sid,
                        latin="",
                        taxon_id=None,
                        photos_added=0,
                        default_set=False,
                        error="species not found",
                    )
                )
                continue
            tasks.append(_task(*entry))

        if tasks:
            done = await asyncio.gather(*tasks)
            results.extend(done)

    return results
