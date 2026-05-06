"""Tog'AI Outdoor Gear — chodir, arqon, sayohat anjomlari.

Har bir mahsulotning sotib olish havolasi Uzum Market'ga tushadi (qidiruv).
Rasmlar — mavzu bo'yicha mos keluvchi Unsplash fotosuratlari.
Run: python manage.py seed_shop
"""
from __future__ import annotations

from decimal import Decimal
from urllib.parse import quote_plus

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from shop.models import Category, Product, ProductImage, CartItem, Wishlist, Review

User = get_user_model()


CATEGORIES = [
    {"name": "Chodirlar", "slug": "chodir", "order": 1,
     "description": "Sayohat, tog' va kemping uchun chodirlar"},
    {"name": "Arqon va karabin", "slug": "arqon-karabin", "order": 2,
     "description": "Toqqa chiqish va xavfsizlik anjomlari"},
    {"name": "Ryukzaklar", "slug": "ryukzak", "order": 3,
     "description": "Trekking sumkalari va kunlik backpack"},
    {"name": "Uxlash anjomlari", "slug": "sleeping", "order": 4,
     "description": "Uxlash xaltasi, gilam, yostiq"},
    {"name": "Kiyim va poyabzal", "slug": "kiyim-poyabzal", "order": 5,
     "description": "Trekking botinkasi, suv o'tkazmas kurtka, fleece"},
    {"name": "Navigatsiya", "slug": "navigatsiya", "order": 6,
     "description": "Kompas, GPS, fonus"},
    {"name": "Suv va idishlar", "slug": "suv-idish", "order": 7,
     "description": "Termos, suv flaska, oshxona"},
    {"name": "Birinchi yordam", "slug": "first-aid", "order": 8,
     "description": "Yo'l shifoxonasi, multitul, ilon zaharidan"},
]


# Stable Unsplash photo IDs that match each outdoor product category.
# These specific photo IDs have been picked manually so each product
# gets a relevant, real-looking image.
def _u(photo_id: str, w: int = 400) -> str:
    # Smaller width + lower quality = much faster on slow networks.
    return f"https://images.unsplash.com/{photo_id}?auto=format&fit=crop&w={w}&q=55"


def _uzum(query: str) -> str:
    return f"https://uzum.uz/uz/search?searchQuery={quote_plus(query)}"


# (title, cat_slug, short, price, discount, photo_id, search_query, brand, featured)
PRODUCTS = [
    # ============= Chodirlar =============
    ("MSR Hubba Hubba 2-kishilik chodir", "chodir",
     "Yengil, suv o'tkazmas, 2 kishilik, 4 fasl chodir",
     5_900_000, 5_200_000,
     "photo-1504280390367-361c6d9f38f4",
     "MSR Hubba Hubba chodir", "MSR", True),
    ("Naturehike Cloud-Up 2", "chodir",
     "20D Silikon, 1.7kg, 2 kishilik, mashhur tog' chodiri",
     1_800_000, 1_550_000,
     "photo-1478131143081-80f7f84ca84d",
     "Naturehike Cloud-Up 2 chodir", "Naturehike", True),
    ("Quechua MH100 3-kishilik chodir", "chodir",
     "Decathlon, suv o'tkazmas, oilaviy, sayohatga ideal",
     1_200_000, None,
     "photo-1504851149312-7a075b496cc7",
     "Quechua MH100 chodir 3", "Quechua", False),
    ("Avtomatik chodir 4-kishilik", "chodir",
     "Bir tortishda ochiladi, oila uchun, plyaj/tog'da",
     950_000, 780_000,
     "photo-1601900059030-b16e88c83feb",
     "avtomatik chodir 4 kishilik", "—", False),

    # ============= Arqon va karabin =============
    ("Petzl Reverso belay/rappel", "arqon-karabin",
     "Yagona/qo'shaloq arqon uchun, 59g, alyuminiy",
     480_000, None,
     "photo-1551632811-561732d1e306",
     "Petzl Reverso belay", "Petzl", True),
    ("Mammut 9.5mm dinamik arqon 60m", "arqon-karabin",
     "UIAA sertifikatlangan, sport va alpinizm uchun",
     2_100_000, 1_850_000,
     "photo-1601933973783-43cf8a7d4c5f",
     "Mammut dinamik arqon 60m", "Mammut", True),
    ("Black Diamond karabin 5x to'plam", "arqon-karabin",
     "Yengil alyuminiy, 24kN, 5 dona",
     320_000, None,
     "photo-1594736797933-d0401ba2fe65",
     "Black Diamond karabin", "Black Diamond", False),
    ("Statik arqon 50m 10.5mm", "arqon-karabin",
     "22kN, qutqaruv va og'irlik tortish uchun",
     1_350_000, None,
     "photo-1517649763962-0c623066013b",
     "statik arqon 10.5mm 50m", "XINDA", False),

    # ============= Ryukzaklar =============
    ("Osprey Atmos AG 65 ryukzak", "ryukzak",
     "65L, Anti-Gravity tizimi, ko'p kunlik trekking premium",
     3_600_000, 3_100_000,
     "photo-1622260614153-03223fb72052",
     "Osprey Atmos 65 ryukzak", "Osprey", True),
    ("Deuter Aircontact 55+10 ryukzak", "ryukzak",
     "65L, ergonomik orqa tizim, og'ir yuk uchun",
     2_900_000, None,
     "photo-1553062407-98eeb64c6a62",
     "Deuter Aircontact ryukzak", "Deuter", True),
    ("Quechua Forclaz 50L trekking", "ryukzak",
     "Suv o'tkazmas qopqoq, oldi-orqa qulflanadigan",
     780_000, 680_000,
     "photo-1559563458-527698bf5295",
     "Quechua Forclaz 50L ryukzak", "Quechua", False),
    ("Daypack 30L kompakt ryukzak", "ryukzak",
     "1 kunlik sayohat, suv shisha + lattop joyi",
     390_000, 320_000,
     "photo-1595953896988-65f9caa8ce06",
     "30L ryukzak kunlik", "—", False),

    # ============= Uxlash anjomlari =============
    ("Uxlash xaltasi -10°C mummy", "sleeping",
     "Mummy formatda, 1.6kg, qishki tog' uchun",
     950_000, 820_000,
     "photo-1496545672447-f699b503d270",
     "uxlash xaltasi mummy -10", "Naturehike", True),
    ("Therm-a-Rest NeoAir gilam", "sleeping",
     "Inflatable, R-value 4.2, 410g, 5 daqiqada shishadi",
     1_650_000, None,
     "photo-1538970272646-f61fabb3a8a2",
     "Therm-a-Rest NeoAir gilam", "Therm-a-Rest", True),
    ("Sayohat yostigi puflanadigan", "sleeping",
     "Kompakt 80g, ergonomik shakl, kemping uchun",
     180_000, None,
     "photo-1547833219-3f0a35b66f81",
     "puflanadigan sayohat yostigi", "Naturehike", False),

    # ============= Kiyim va poyabzal =============
    ("Salomon X Ultra 4 GTX trekking botinka", "kiyim-poyabzal",
     "Gore-Tex, suv o'tkazmas, qattiq toshli yo'lda barqaror",
     2_400_000, 2_050_000,
     "photo-1542838132-92c53300491e",
     "Salomon X Ultra GTX botinka", "Salomon", True),
    ("La Sportiva Trango Tower GTX", "kiyim-poyabzal",
     "Yuqori toqqa chiqish uchun mustahkam botinka",
     3_900_000, None,
     "photo-1551107696-a4b0c5a0d9a2",
     "La Sportiva Trango botinka", "La Sportiva", False),
    ("Patagonia Torrentshell 3L kurtka", "kiyim-poyabzal",
     "Suv o'tkazmas membrana, 3 qatlamli, yengil",
     2_600_000, 2_300_000,
     "photo-1551028719-00167b16eac5",
     "yomgir kurtkasi membrana", "Patagonia", True),
    ("Fleece kurtka 200gr", "kiyim-poyabzal",
     "Issiq, nafas oluvchi, qatlam ostiga",
     520_000, 440_000,
     "photo-1591047139829-d91aecb6caea",
     "fleece kurtka erkaklar", "Quechua", False),

    # ============= Navigatsiya =============
    ("Suunto MC-2 Pro kompass", "navigatsiya",
     "Aniq, oyna bilan, harbiy uchun ham mos",
     580_000, None,
     "photo-1454942901704-3c44c11b2ad1",
     "Suunto MC-2 kompass", "Suunto", True),
    ("Garmin eTrex 22x GPS", "navigatsiya",
     "GLONASS+GPS, 25 soat batareya, harita ichida",
     3_200_000, 2_800_000,
     "photo-1587293852726-70cdb56c2866",
     "Garmin eTrex GPS", "Garmin", True),
    ("Petzl Actik Core boshli fonus", "navigatsiya",
     "450 lyumen, qayta zaryadli, 6 rejim",
     680_000, 580_000,
     "photo-1473445730015-841f29a9490b",
     "Petzl Actik boshli fonus", "Petzl", False),
    ("LED Lenser P7R Core 1400lm fonus", "navigatsiya",
     "Qo'l fonusi, USB-C, 21 soat batareya",
     780_000, None,
     "photo-1581094488379-6f1a16b18f5d",
     "LED Lenser fonus 1400 lyumen", "LED Lenser", False),

    # ============= Suv va idishlar =============
    ("Hydro Flask 1L vakuum termos", "suv-idish",
     "24h sovuq / 12h issiq, po'lat",
     520_000, 460_000,
     "photo-1602143407151-7111542de6e8",
     "Hydro Flask 1L termos", "Hydro Flask", True),
    ("MSR Pocket Rocket 2 gaz pechka", "suv-idish",
     "73g, 1L suvni 3.5 daqiqada qaynatadi",
     720_000, None,
     "photo-1598548669499-fcc4f5b0e67c",
     "MSR Pocket Rocket gaz pechka", "MSR", True),
    ("Sayohat termosi 750ml", "suv-idish",
     "Po'lat, 24 soat issiq, sayohat uchun ideal",
     180_000, 145_000,
     "photo-1550501579-31a36b7e4076",
     "termos 750 ml sayohat", "—", False),
    ("LifeStraw shaxsiy suv filtri", "suv-idish",
     "4000L gacha, 99.9999% bakteriya tutadi",
     420_000, 360_000,
     "photo-1530541930197-ff16ac917b0e",
     "LifeStraw suv filtri", "LifeStraw", True),

    # ============= Birinchi yordam =============
    ("Adventure Medical UltraLight kit", "first-aid",
     "Trekking uchun yengil first-aid to'plam",
     420_000, None,
     "photo-1603398938378-e54eab446dde",
     "first aid kit ultralight", "Adventure Medical", False),
    ("Sawyer Extractor — ilon zahari so'rgich", "first-aid",
     "Ilon, ari, chayonga zudlik bilan yordam",
     220_000, 175_000,
     "photo-1586773860418-d37222d8fce3",
     "ilon zahari sorgich Sawyer", "Sawyer", True),
    ("Termal yopinchiq emergency", "first-aid",
     "Mylar 213x132 sm, jarohat / sovuqda",
     30_000, 22_000,
     "photo-1576091160550-2173dba999ef",
     "emergency mylar yopinchiq", "—", False),
    ("Leatherman 14-in-1 multitul", "first-aid",
     "Pichoq, qaychi, fayl, otvyortka — sayohatda zarur",
     820_000, 720_000,
     "photo-1581094288338-2314dddb7ece",
     "Leatherman multitul", "Leatherman", True),
]


class Command(BaseCommand):
    help = "Reset shop and seed outdoor / hiking products with Uzum links"

    def add_arguments(self, parser):
        parser.add_argument("--keep", action="store_true",
                            help="Keep existing rows instead of wiping")

    @transaction.atomic
    def handle(self, *args, **opts):
        seller, _ = User.objects.get_or_create(
            phone="+998900000000",
            defaults={
                "full_name": "Tog'AI Bozor",
                "account_type": "seller",
                "seller_name": "Tog'AI Outdoor",
                "seller_verified": True,
                "is_active": True,
            },
        )

        if not opts["keep"]:
            CartItem.objects.all().delete()
            Wishlist.objects.all().delete()
            Review.objects.all().delete()
            ProductImage.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write(self.style.WARNING("✗ All shop data wiped"))

        cat_map = {}
        for cd in CATEGORIES:
            cat, _ = Category.objects.update_or_create(
                slug=cd["slug"],
                defaults={
                    "name": cd["name"],
                    "order": cd["order"],
                    "description": cd["description"],
                    "is_active": True,
                },
            )
            cat_map[cd["slug"]] = cat

        new_count = 0
        for (title, cat_slug, short, price, disc,
             photo_id, search_query, brand, featured) in PRODUCTS:
            cat = cat_map.get(cat_slug)
            if not cat:
                continue
            _, was_created = Product.objects.update_or_create(
                title=title,
                defaults={
                    "seller": seller,
                    "category": cat,
                    "short_description": short,
                    "description": short,
                    "price": Decimal(str(price)),
                    "discount_price": Decimal(str(disc)) if disc else None,
                    "currency": "UZS",
                    "stock_quantity": 50,
                    "status": "active",
                    "is_featured": featured,
                    "rating": Decimal("4.5"),
                    "reviews_count": 12,
                    "image_url": _u(photo_id),
                    "external_url": _uzum(search_query),
                    "external_seller": "Uzum Market",
                    "brand": brand,
                },
            )
            if was_created:
                new_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"✓ {len(CATEGORIES)} kategoriya, {len(PRODUCTS)} mahsulot "
            f"({new_count} yangi). Hammasi Uzum linkiga ulangan."
        ))
