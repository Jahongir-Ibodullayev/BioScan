"""Seed data — Django'siz, FastAPI o'zi yuklaydi.

Ishlatish:
    ./venv/bin/python -m scripts.seed
yoki:
    ./venv/bin/python scripts/seed.py

Yuklanadigan ma'lumotlar:
  - 13 Region (O'zbekiston viloyatlari)
  - Crop ekinlar (scripts/seed_crops.json)
  - Catalog species (asosiy 6 ta + 30+ Qizil kitob)

Idempotent — qayta ishga tushirsa, mavjudini yangilaydi.
"""
from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.session import AsyncSessionLocal, _get_engine
from app.models.crops import Crop, Region
from app.models.species import Species

HERE = Path(__file__).parent


# ----------------------------------------------------------------------
# REGIONS (Django crops/fixtures/seed_regions.json'dan)
# ----------------------------------------------------------------------
async def seed_regions(db):
    path = HERE / "seed_regions.json"
    if not path.exists():
        print("  ! seed_regions.json topilmadi, skip")
        return 0
    raw = json.loads(path.read_text())
    n = 0
    for item in raw:
        if isinstance(item, dict) and "fields" in item:
            data = item["fields"]
        else:
            data = item
        stmt = pg_insert(Region.__table__).values(**data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["slug"],
            set_={k: v for k, v in data.items() if k != "slug"},
        )
        await db.execute(stmt)
        n += 1
    await db.commit()
    return n


# ----------------------------------------------------------------------
# CROPS (Django seed_crops.json'dan)
# ----------------------------------------------------------------------
async def seed_crops(db):
    path = HERE / "seed_crops.json"
    if not path.exists():
        print("  ! seed_crops.json topilmadi, skip")
        return 0
    raw = json.loads(path.read_text())
    n = 0
    for item in raw:
        data = item.get("fields", item) if isinstance(item, dict) else item
        # Django Decimal'larni str'ga aylanmasin
        if "ph_min" in data:
            data["ph_min"] = Decimal(str(data["ph_min"]))
        if "ph_max" in data:
            data["ph_max"] = Decimal(str(data["ph_max"]))
        # updated_at majburiy bo'lsa server defaultiga tashlaymiz
        data.pop("updated_at", None)
        stmt = pg_insert(Crop.__table__).values(**data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["slug"],
            set_={k: v for k, v in data.items() if k != "slug"},
        )
        await db.execute(stmt)
        n += 1
    await db.commit()
    return n


# ----------------------------------------------------------------------
# CATALOG SPECIES (Django seed.py + seed_redbook.py'dan)
# ----------------------------------------------------------------------
BASE_SPECIES = [
    {
        "slug": "isiriq", "name": "Isiriq", "latin": "Peganum harmala",
        "category": "giyoh", "icon_name": "leaf",
        "color_class": "bg-primary-100 text-primary-700",
        "red_book": True, "iucn_status": "LC", "is_medicinal": True,
        "summary": "Markaziy Osiyo tog'larida keng tarqalgan, shifobaxsh va zaharli xususiyatlarga ega ko'p yillik o'simlik.",
        "description": "Isiriq — Peganum harmala — xalq tabobatida asrlar davomida ishlatilib kelayotgan ko'p yillik o'simlik.",
        "habitat": "Qoyali yonbag'irlar, 600–1800 m balandlik, quruq tuproq.",
        "uses": "Tutatib xonani poklash, sovuq oldi profilaktikasi.",
        "warnings": "Katta miqdorda qabul qilinsa, gallyutsinatsiya va yurak ishi buzilishiga olib keladi.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/94/Peganum_harmala_003.JPG/800px-Peganum_harmala_003.JPG",
        "regions": "Markaziy Osiyo, Shahrisabz tog'lari",
    },
    {
        "slug": "yovvoyi-yongoq", "name": "Yovvoyi yong'oq", "latin": "Juglans regia",
        "category": "daraxt", "icon_name": "tree",
        "color_class": "bg-amber-100 text-amber-700",
        "red_book": False, "iucn_status": "NT", "is_edible": True,
        "summary": "Tog' daralarida uchraydigan, mevasi to'yimli va shifobaxsh daraxt.",
        "description": "Yovvoyi yong'oq daraxti 25 metrgacha o'sadi, 300 yilgacha yashaydi.",
        "habitat": "Nam daralar, soyali yonbag'irlar, 1200–2200 m.",
        "uses": "Meva ozuqa sifatida, yaprog'i — choy; yog'ochi qurilishda.",
        "regions": "O'zbekiston tog'lari, G'arbiy Tyan-Shan",
    },
    {
        "slug": "tog-archa", "name": "Tog' archa", "latin": "Juniperus communis",
        "category": "daraxt", "icon_name": "tree",
        "color_class": "bg-emerald-100 text-emerald-700",
        "red_book": True, "iucn_status": "LC", "is_medicinal": True,
        "summary": "Salomatlik uchun foydali havo beruvchi, yong'inga chidamli tog' daraxti.",
        "description": "Tog' archa o'ta sekin o'sadi, 500 yilgacha yashaydi.",
        "habitat": "Tosh tuproq, shamolli cho'qqilar, 1500–3000 m.",
        "uses": "Efir moyi, havo poklash, manzarali o'rmon.",
        "warnings": "Shox-shabbasini kesish qat'iyan taqiqlanadi.",
        "regions": "G'arbiy Tyan-Shan, Pomir-Oloy",
    },
    {
        "slug": "qizil-lola", "name": "Qizil lola", "latin": "Tulipa greigii",
        "category": "gul", "icon_name": "flower",
        "color_class": "bg-rose-100 text-rose-700",
        "red_book": True, "iucn_status": "VU",
        "summary": "Bahorda tog'lar yon bag'rini qizilga bo'yaydi, Qizil kitobga kiritilgan.",
        "description": "Tulipa greigii O'zbekiston endemigi hisoblanadi. Aprel–may oylarida gullaydi.",
        "habitat": "Toshli dashtlar, 700–2500 m.",
        "warnings": "Terib olish — jarima.",
        "regions": "O'zbekiston endemigi",
        "fine_bhm_min": 50, "fine_bhm_max": 150, "law_article": "MK 204-modda",
    },
    {
        "slug": "orta-osiyo-gurzasi", "name": "O'rta Osiyo gurzasi",
        "latin": "Macrovipera lebetina",
        "category": "jonivor", "icon_name": "snake",
        "color_class": "bg-danger-light text-danger",
        "red_book": False, "iucn_status": "LC",
        "summary": "O'lkamizning eng zaharli ilonlaridan biri.",
        "description": "1.5 metrgacha uzunlikka yetadi. Zahari hemotoksik.",
        "habitat": "Qoyali yonbag'irlar, tosh uyumlari, quruq dalalar.",
        "warnings": "Bosib qolmang.",
        "first_aid": "1) Tinch bo'ling. 2) Chaqqan joyni pastroq tuting. 3) 103.",
        "regions": "Markaziy Osiyo",
        "livestock_danger": "deadly",
    },
    {
        "slug": "qora-chayon", "name": "Qora chayon", "latin": "Orthochirus scrobiculosus",
        "category": "hasharot", "icon_name": "paw",
        "color_class": "bg-slate-100 text-slate-700",
        "red_book": False, "iucn_status": "LC",
        "summary": "Tunda faol, qoyalar ostida yashiringan, kichik ammo og'riqli chayon.",
        "description": "Uzunligi 5–7 sm. Zahari asab tizimiga ta'sir qiladi.",
        "habitat": "Tosh ostlari, yoriqlar, quruq qumli joylar.",
        "first_aid": "Chaqqan joyni muzlatib, anti-gistamin tabletka ichib, shifokorga.",
        "regions": "O'zbekiston janubi, Turkmaniston",
    },
]


REDBOOK_SPECIES = [
    {"slug": "uncia-uncia", "name": "Ilvirs", "latin": "Lynx lynx isabellinus",
     "category": "jonivor", "icon_name": "paw", "red_book": True, "iucn_status": "EN",
     "summary": "Tog' silovsini. Noyob turkman turi.",
     "habitat": "Tog' o'rmonlari", "regions": "Zarafshon, G'arbiy Tyan-Shan",
     "fine_bhm_min": 300, "fine_bhm_max": 600, "law_article": "Jinoiy 202-modda"},
    {"slug": "saiga-tatarica", "name": "Sayg'oq", "latin": "Saiga tatarica",
     "category": "jonivor", "icon_name": "paw", "red_book": True, "iucn_status": "CR",
     "summary": "Kritik xavfda. Brakonerlik tufayli.",
     "habitat": "Ustyurt cho'li", "warnings": "Kritik holatda. Ov — jinoiy jihat.",
     "regions": "Qoraqalpog'iston, Ustyurt",
     "fine_bhm_min": 800, "fine_bhm_max": 1500, "law_article": "Jinoiy 202-modda"},
    {"slug": "gazella-subgutturosa", "name": "Jayran", "latin": "Gazella subgutturosa",
     "category": "jonivor", "icon_name": "paw", "red_book": True, "iucn_status": "VU",
     "summary": "O'rta Osiyo cho'l gazellesi.",
     "habitat": "Qizilqum, Ustyurt", "regions": "Markaziy-g'arbiy UZ",
     "fine_bhm_min": 400, "fine_bhm_max": 800, "law_article": "Jinoiy 202-modda"},
    {"slug": "ursus-arctos-isabellinus", "name": "Tyan-Shan ayig'i",
     "latin": "Ursus arctos isabellinus",
     "category": "jonivor", "icon_name": "paw", "red_book": True, "iucn_status": "LC",
     "summary": "Kichik subturi. O'zbekistonda noyob.",
     "habitat": "Baland tog' o'rmonlari", "regions": "Chotqol, G'arbiy Tyan-Shan",
     "fine_bhm_min": 600, "fine_bhm_max": 1200, "law_article": "Jinoiy 202-modda"},
    {"slug": "marmota-menzbieri", "name": "Menzbir suvarakmurti",
     "latin": "Marmota menzbieri",
     "category": "jonivor", "icon_name": "paw", "red_book": True, "iucn_status": "EN",
     "summary": "Tyan-Shan subalp yaylovlari endemigi.",
     "habitat": "Alp yaylovlari, 2500-3500m", "regions": "G'arbiy Tyan-Shan",
     "fine_bhm_min": 100, "fine_bhm_max": 300, "law_article": "Jinoiy 202-modda"},
    {"slug": "chlamydotis-macqueenii", "name": "Johildqaldirg'och",
     "latin": "Chlamydotis macqueenii",
     "category": "qush", "icon_name": "paw", "red_book": True, "iucn_status": "VU",
     "summary": "Cho'l johildqaldirg'ochi.",
     "habitat": "Dasht-cho'l", "regions": "Qizilqum, Ustyurt",
     "fine_bhm_min": 200, "fine_bhm_max": 500, "law_article": "Jinoiy 202-modda"},
    {"slug": "aquila-heliaca", "name": "Qora burgut", "latin": "Aquila heliaca",
     "category": "qush", "icon_name": "paw", "red_book": True, "iucn_status": "VU",
     "summary": "Eng kuchli bo'yinbosar yirtqich qush.",
     "habitat": "Cho'l va tog' ostlari", "regions": "Butun UZ",
     "fine_bhm_min": 300, "fine_bhm_max": 700, "law_article": "Jinoiy 202-modda"},
    {"slug": "falco-cherrug", "name": "Lochin", "latin": "Falco cherrug",
     "category": "qush", "icon_name": "paw", "red_book": True, "iucn_status": "EN",
     "summary": "Ov qushi. Jahon bozorida noqonuniy sotiladi.",
     "habitat": "Tog' va dasht", "regions": "Barcha UZ",
     "fine_bhm_min": 500, "fine_bhm_max": 1000, "law_article": "Jinoiy 202-modda"},
    {"slug": "parnassius-apollo", "name": "Apollon kapalagi",
     "latin": "Parnassius apollo",
     "category": "hasharot", "icon_name": "paw", "red_book": True, "iucn_status": "VU",
     "summary": "Tog' kapalagi. Kolleksiyachilar tufayli kam.",
     "habitat": "Tog' yaylovlari", "regions": "Tog'li UZ",
     "fine_bhm_min": 30, "fine_bhm_max": 80, "law_article": "MK 204-modda"},
    {"slug": "varanus-griseus", "name": "Kulrang varan", "latin": "Varanus griseus",
     "category": "jonivor", "icon_name": "snake", "red_book": True, "iucn_status": "LC",
     "summary": "O'zbek cho'l drakonchasi.",
     "habitat": "Qizilqum", "regions": "Markaziy UZ",
     "fine_bhm_min": 80, "fine_bhm_max": 200, "law_article": "MK 204-modda"},
    {"slug": "testudo-horsfieldii", "name": "O'rta osiyo toshbaqasi",
     "latin": "Testudo horsfieldii",
     "category": "jonivor", "icon_name": "paw", "red_book": True, "iucn_status": "VU",
     "summary": "Brakonerlar tomonidan eksport uchun tutiladi.",
     "habitat": "Cho'l-dasht", "regions": "Barcha quruq UZ",
     "fine_bhm_min": 50, "fine_bhm_max": 120, "law_article": "MK 204-modda"},
    # Asalbop / Dorivor / Halol filter uchun
    {"slug": "trifolium-pratense", "name": "Qizil sebarga",
     "latin": "Trifolium pratense",
     "category": "giyoh", "icon_name": "leaf", "red_book": False, "iucn_status": "LC",
     "summary": "Asalari uchun eng yaxshi giyoh.",
     "is_honey_plant": True, "is_edible": True, "halal_status": "halal",
     "uses": "Asalari nektar manbai.", "bloom_months": "5,6,7", "regions": "Butun UZ"},
    {"slug": "origanum-vulgare", "name": "Tog' rayhon", "latin": "Origanum vulgare",
     "category": "giyoh", "icon_name": "leaf", "red_book": False, "iucn_status": "LC",
     "summary": "Tog' giyohi, dorivor.",
     "is_medicinal": True, "is_edible": True, "is_honey_plant": True,
     "halal_status": "halal",
     "uses": "Choy, damlama, ovqatga ziravor.",
     "bloom_months": "6,7,8", "regions": "Tog' yon bag'ri"},
    {"slug": "hyoscyamus-niger", "name": "Mingdevona", "latin": "Hyoscyamus niger",
     "category": "giyoh", "icon_name": "leaf", "red_book": False, "iucn_status": "LC",
     "summary": "Zaharli o't.", "livestock_danger": "deadly",
     "warnings": "Chorva yeydi → yoppasiga o'lim.",
     "halal_status": "haram", "regions": "Dasht, cho'l"},
]


async def seed_species(db):
    n = 0
    for s in BASE_SPECIES + REDBOOK_SPECIES:
        stmt = pg_insert(Species.__table__).values(**s)
        stmt = stmt.on_conflict_do_update(
            index_elements=["slug"],
            set_={k: v for k, v in s.items() if k != "slug"},
        )
        await db.execute(stmt)
        n += 1
    await db.commit()
    return n


async def main():
    print("🌱 BioScan seed boshlandi...")
    async with AsyncSessionLocal() as db:
        r = await seed_regions(db)
        print(f"  ✓ Regions: {r}")
        c = await seed_crops(db)
        print(f"  ✓ Crops: {c}")
        s = await seed_species(db)
        print(f"  ✓ Species: {s}")

        # Yakuniy hisob
        from sqlalchemy import func
        total_sp = await db.scalar(select(func.count()).select_from(Species))
        total_cr = await db.scalar(select(func.count()).select_from(Crop))
        total_rg = await db.scalar(select(func.count()).select_from(Region))
        print()
        print("📊 Hozirgi DB holati:")
        print(f"   Species : {total_sp}")
        print(f"   Crops   : {total_cr}")
        print(f"   Regions : {total_rg}")

    await _get_engine().dispose()
    print("\n✅ Seed tugadi")


if __name__ == "__main__":
    asyncio.run(main())
