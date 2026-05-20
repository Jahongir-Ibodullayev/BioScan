"""scripts/enrich_inat.py — barcha turlarni iNat'dan boyitadi.

Foydalanish:
    python -m scripts.enrich_inat                 # barchasi, faqat yangi rasmlar
    python -m scripts.enrich_inat --replace       # mavjud rasmlarni o'chirib qayta to'plash
    python -m scripts.enrich_inat --limit 10      # birinchi 10 ta tur (test)
    python -m scripts.enrich_inat --slug salmo-trutta-oxianus   # bitta tur
    python -m scripts.enrich_inat --category baliq --concurrency 6
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time

from sqlalchemy import select

from app.db.session import _get_sessionmaker, dispose_engine
from app.models.species import Species
from app.services.inat_enrich import enrich_many


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="enrich_inat",
        description="iNaturalist'dan turlarga rasm va metama'lumot to'playdi.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Mavjud rasmlarni o'chirib qayta to'plash (default: faqat yangi rasm qo'shadi)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Birinchi N ta turni ishlash (test uchun)",
    )
    parser.add_argument(
        "--slug",
        type=str,
        default=None,
        metavar="S",
        help="Faqat bitta turni boyitish (slug bo'yicha)",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        metavar="C",
        help="Faqat berilgan kategoriya turlarini boyitish (masalan: baliq, qush, o'simlik)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        metavar="N",
        help="Parallel iNat so'rovlari soni (default: 4)",
    )
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> int:
    sessionmaker = _get_sessionmaker()

    # 1) SELECT species filtered by args
    stmt = select(Species).order_by(Species.id)
    if args.slug:
        stmt = stmt.where(Species.slug == args.slug)
    if args.category:
        stmt = stmt.where(Species.category == args.category)
    if args.limit is not None and args.limit > 0:
        stmt = stmt.limit(args.limit)

    async with sessionmaker() as db:
        result = await db.execute(stmt)
        species_list = list(result.scalars().all())

        if not species_list:
            print("Hech qanday tur topilmadi (filtr juda tor bo'lishi mumkin).")
            return 0

        total = len(species_list)
        slug_by_id = {s.id: s.slug for s in species_list}
        species_ids = [s.id for s in species_list]

        print(f"Boyitiladigan turlar: {total} ta (concurrency={args.concurrency}, replace={args.replace})")
        started = time.monotonic()

        # 2) Call enrich_many
        try:
            results = await enrich_many(species_ids, db, concurrency=args.concurrency)
        except asyncio.CancelledError:
            print("\n[!] Bekor qilindi (Ctrl+C).")
            raise

        # 3) Print progress per result
        total_photos = 0
        errors: list[tuple[str, str]] = []
        for idx, res in enumerate(results, start=1):
            sid = getattr(res, "species_id", None)
            slug = slug_by_id.get(sid, str(sid))
            error = getattr(res, "error", None)
            photos = getattr(res, "photos_added", 0) or 0
            default = getattr(res, "default_url", None) or getattr(res, "default", None) or ""

            if error:
                errors.append((slug, str(error)))
                print(f"[{idx}/{total}] {slug}: ERROR — {error}")
            else:
                total_photos += int(photos)
                default_str = f" (default={default})" if default else ""
                print(f"[{idx}/{total}] {slug}: {photos} photos added{default_str}")

        elapsed = time.monotonic() - started

        # 4) Summary
        print()
        print("=" * 60)
        print(f"Jami ishlangan turlar: {total}")
        print(f"Jami qo'shilgan rasmlar: {total_photos}")
        print(f"Xatolar: {len(errors)}")
        if errors:
            for slug, err in errors:
                print(f"  - {slug}: {err}")
        print(f"Vaqt: {elapsed:.1f}s")
        print("=" * 60)

        return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        return asyncio.run(_run_with_dispose(args))
    except KeyboardInterrupt:
        print("\n[!] Foydalanuvchi tomonidan to'xtatildi.")
        return 1


async def _run_with_dispose(args: argparse.Namespace) -> int:
    try:
        return await _run(args)
    except asyncio.CancelledError:
        return 1
    finally:
        try:
            await dispose_engine()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
