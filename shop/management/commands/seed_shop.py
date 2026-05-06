"""
Tog'AI Outdoor Gear — chodir, arqon, sayohat anjomlari.

Faqat tabiatda yuradigan turistlar uchun: chodir, uxlash xaltasi, arqon,
fonarlar, kompas, multi-tool, suv tozalovchi, birinchi yordam va h.k.

Har mahsulotda Unsplash CC0 rasmi va Amazon/Aliexpress sotib olish havolasi.
"""
from __future__ import annotations

import random
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from shop.models import Category, Product

User = get_user_model()


# ============================================================
# Faqat 4 ta outdoor kategoriya — ovqat/giyoh/asal yo'q
# ============================================================
CATEGORIES = [
    {"name": "Chodir va uxlash", "slug": "tent",     "order": 1},
    {"name": "Arqon va alpinizm","slug": "climbing", "order": 2},
    {"name": "Sayohat anjomlari","slug": "gear",     "order": 3},
    {"name": "Xavfsizlik",       "slug": "safety",   "order": 4},
]

SELLERS = [
    {"phone": "+998900000001", "full_name": "Tog'AI Bozori",     "seller_name": "Tog'AI Bozori"},
    {"phone": "+998900000002", "full_name": "Chimgan Trail",      "seller_name": "Chimgan Trail"},
    {"phone": "+998900000003", "full_name": "Outdoor UZ",         "seller_name": "Outdoor UZ"},
]

# ============================================================
# (title, price_so'm, image_url, external_url, seller)
# Aliexpress va Amazon search havolalarini qo'llaymiz — affiliate-friendly.
# ============================================================
PRODUCTS = {
    "tent": [
        ("4 kishilik suv o'tkazmas chodir", 950_000,
         "https://images.unsplash.com/photo-1504280390367-361c6d9f38f4",
         "https://www.aliexpress.com/wholesale-4-person-tent.html", "Aliexpress"),
        ("2 kishilik yengil chodir (1.8kg)", 680_000,
         "https://images.unsplash.com/photo-1487730116645-74489c95b41b",
         "https://www.aliexpress.com/wholesale-2-person-ultralight-tent.html", "Aliexpress"),
        ("Tog' uxlash xaltasi -10°C", 540_000,
         "https://images.unsplash.com/photo-1496080174650-637e3f22fa03",
         "https://www.aliexpress.com/wholesale-sleeping-bag--10-degree.html", "Aliexpress"),
        ("Yengil sayohat gilamchasi (foam)", 180_000,
         "https://images.unsplash.com/photo-1571687949921-1306bfb24b72",
         "https://www.aliexpress.com/wholesale-sleeping-pad-foam.html", "Aliexpress"),
        ("Hammock — daraxtga osiladigan", 220_000,
         "https://images.unsplash.com/photo-1504851149312-7a075b496cc7",
         "https://www.aliexpress.com/wholesale-camping-hammock.html", "Aliexpress"),
        ("Tarpaulin (suvga qarshi yopgich)", 145_000,
         "https://images.unsplash.com/photo-1505568571-7a3eef41c01b",
         "https://www.aliexpress.com/wholesale-tarpaulin-camping.html", "Aliexpress"),
        ("Yostiq — havoli sayohat uchun", 75_000,
         "https://images.unsplash.com/photo-1519377345644-937ef9754740",
         "https://www.aliexpress.com/wholesale-camping-pillow.html", "Aliexpress"),
        ("Termo gilam (qishki uxlash)", 290_000,
         "https://images.unsplash.com/photo-1500376820431-19b46db17b4f",
         "https://www.aliexpress.com/wholesale-thermal-sleeping-pad.html", "Aliexpress"),
    ],
    "climbing": [
        ("Tog' arqoni 50m (10mm dynamic)", 950_000,
         "https://images.unsplash.com/photo-1551655510-555dc3be8633",
         "https://www.aliexpress.com/wholesale-climbing-rope-50m.html", "Aliexpress"),
        ("Yengil yordamchi arqon 30m (8mm)", 380_000,
         "https://images.unsplash.com/photo-1604588519830-e1d7c2c61dca",
         "https://www.aliexpress.com/wholesale-static-rope-30m.html", "Aliexpress"),
        ("Karabin to'plami (5 dona, dynamic)", 240_000,
         "https://images.unsplash.com/photo-1486528957538-b13e4c8e5b8a",
         "https://www.aliexpress.com/wholesale-climbing-carabiner-set.html", "Aliexpress"),
        ("Alpinizm kamari (harness)", 380_000,
         "https://images.unsplash.com/photo-1606857521015-7f9fcf423740",
         "https://www.aliexpress.com/wholesale-climbing-harness.html", "Aliexpress"),
        ("Helmet — toshdan himoya", 290_000,
         "https://images.unsplash.com/photo-1606857521015-7f9fcf423740",
         "https://www.aliexpress.com/wholesale-climbing-helmet.html", "Aliexpress"),
        ("Belay device + carabiner", 195_000,
         "https://images.unsplash.com/photo-1551655510-555dc3be8633",
         "https://www.aliexpress.com/wholesale-belay-device.html", "Aliexpress"),
        ("Crampons (muzga qarshi)", 420_000,
         "https://images.unsplash.com/photo-1551524559-8af4e6624178",
         "https://www.aliexpress.com/wholesale-mountaineering-crampons.html", "Aliexpress"),
        ("Ice axe (muz cho'qmori)", 480_000,
         "https://images.unsplash.com/photo-1551524559-8af4e6624178",
         "https://www.aliexpress.com/wholesale-ice-axe.html", "Aliexpress"),
        ("Telescopic sayohat tayoq (juft)", 195_000,
         "https://images.unsplash.com/photo-1551632811-561732d1e306",
         "https://www.aliexpress.com/wholesale-trekking-poles.html", "Aliexpress"),
        ("Climbing chalk + xalta", 95_000,
         "https://images.unsplash.com/photo-1522163182402-834f871fd851",
         "https://www.aliexpress.com/wholesale-climbing-chalk-bag.html", "Aliexpress"),
    ],
    "gear": [
        ("Tog' ryukzaki 60L", 750_000,
         "https://images.unsplash.com/photo-1553062407-98eeb64c6a62",
         "https://www.aliexpress.com/wholesale-hiking-backpack-60l.html", "Aliexpress"),
        ("Yengil sayohat ryukzaki 30L", 420_000,
         "https://images.unsplash.com/photo-1622560480605-d83c853bc5c3",
         "https://www.aliexpress.com/wholesale-daypack-30l.html", "Aliexpress"),
        ("Suv qopi (hydration bladder 2L)", 115_000,
         "https://images.unsplash.com/photo-1559827260-dc66d52bef19",
         "https://www.aliexpress.com/wholesale-hydration-bladder.html", "Aliexpress"),
        ("Termal flyaga 750ml", 130_000,
         "https://images.unsplash.com/photo-1602143407151-7111542de6e8",
         "https://www.aliexpress.com/wholesale-thermos-flask.html", "Aliexpress"),
        ("Quyosh batareyali fonar", 220_000,
         "https://images.unsplash.com/photo-1507525428034-b723cf961d3e",
         "https://www.aliexpress.com/wholesale-solar-camping-lantern.html", "Aliexpress"),
        ("Bosh fonar LED 600 lumen", 165_000,
         "https://images.unsplash.com/photo-1551415923-a2297c7fda79",
         "https://www.aliexpress.com/wholesale-led-headlamp.html", "Aliexpress"),
        ("Mini gaz pechka (sayohat)", 225_000,
         "https://images.unsplash.com/photo-1517483000871-1dbf64a6e1c6",
         "https://www.aliexpress.com/wholesale-mini-camping-stove.html", "Aliexpress"),
        ("Sayohat oshxona to'plami (qozon+tova)", 285_000,
         "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136",
         "https://www.aliexpress.com/wholesale-camping-cookware.html", "Aliexpress"),
        ("Suv tozalovchi filtr", 320_000,
         "https://images.unsplash.com/photo-1560089165-5b96a6ed4b1c",
         "https://www.aliexpress.com/wholesale-water-filter-camping.html", "Aliexpress"),
        ("Multi-asbob (16-in-1)", 380_000,
         "https://images.unsplash.com/photo-1574870111867-089730e5a72b",
         "https://www.aliexpress.com/wholesale-multi-tool.html", "Aliexpress"),
        ("Sayohat pichoq (tactical, sheath bilan)", 240_000,
         "https://images.unsplash.com/photo-1593504049359-74330189a345",
         "https://www.aliexpress.com/wholesale-survival-knife.html", "Aliexpress"),
        ("Kichik bolta (camping axe)", 295_000,
         "https://images.unsplash.com/photo-1567113463300-102a7eb3cb26",
         "https://www.aliexpress.com/wholesale-camping-hatchet.html", "Aliexpress"),
        ("Tashqi power-bank 20000mAh", 290_000,
         "https://images.unsplash.com/photo-1609592424823-58a5e0e6ca9e",
         "https://www.aliexpress.com/wholesale-power-bank-20000mah.html", "Aliexpress"),
        ("Quyosh paneli (yengil, taxlanadigan)", 480_000,
         "https://images.unsplash.com/photo-1509391366360-2e959784a276",
         "https://www.aliexpress.com/wholesale-foldable-solar-panel-camping.html", "Aliexpress"),
        ("Termo qopqoqli stakan 350ml", 95_000,
         "https://images.unsplash.com/photo-1485808191679-5f86510681a2",
         "https://www.aliexpress.com/wholesale-thermos-mug.html", "Aliexpress"),
        ("Yong'in chaqirish o'choqi (firestarter)", 78_000,
         "https://images.unsplash.com/photo-1517398741578-6cf8b62b95cf",
         "https://www.aliexpress.com/wholesale-fire-starter-camping.html", "Aliexpress"),
        ("Kompas + xarita (mexanik)", 95_000,
         "https://images.unsplash.com/photo-1518831959646-742c3a14ebf7",
         "https://www.aliexpress.com/wholesale-hiking-compass.html", "Aliexpress"),
        ("Binokl 10x42 (HD prizma)", 580_000,
         "https://images.unsplash.com/photo-1486820599267-578da3ab4944",
         "https://www.aliexpress.com/wholesale-binoculars-10x42.html", "Aliexpress"),
        ("GPS qurilma (tracker)", 950_000,
         "https://images.unsplash.com/photo-1584489451960-0d07d8b79d75",
         "https://www.aliexpress.com/wholesale-gps-tracker-hiking.html", "Aliexpress"),
        ("Qum/chang himoyali yopgich (rain cover)", 95_000,
         "https://images.unsplash.com/photo-1496318447583-f524534e9ce1",
         "https://www.aliexpress.com/wholesale-backpack-rain-cover.html", "Aliexpress"),
    ],
    "safety": [
        ("Birinchi yordam to'plami (kompakt)", 145_000,
         "https://images.unsplash.com/photo-1603398938378-e54eab446dde",
         "https://www.aliexpress.com/wholesale-first-aid-kit-camping.html", "Aliexpress"),
        ("Ilon zaharidan extractor pump", 85_000,
         "https://images.unsplash.com/photo-1550831107-1553da8c8464",
         "https://www.aliexpress.com/wholesale-snake-bite-kit.html", "Aliexpress"),
        ("Acil signal hushtak + oyna", 35_000,
         "https://images.unsplash.com/photo-1543013309-0d8e7a3a1b2a",
         "https://www.aliexpress.com/wholesale-emergency-whistle-survival.html", "Aliexpress"),
        ("Acil termal blanket (mylar 4-pack)", 55_000,
         "https://images.unsplash.com/photo-1511497584788-876760111969",
         "https://www.aliexpress.com/wholesale-emergency-mylar-blanket.html", "Aliexpress"),
        ("Yer kana (insect) repellent", 65_000,
         "https://images.unsplash.com/photo-1556228720-195a672e8a03",
         "https://www.aliexpress.com/wholesale-insect-repellent-deet.html", "Aliexpress"),
        ("Quyoshdan himoya krem SPF50+", 75_000,
         "https://images.unsplash.com/photo-1556228852-80b6e5eeff06",
         "https://www.aliexpress.com/wholesale-sunscreen-spf50-outdoor.html", "Aliexpress"),
        ("Kichik o't o'chiruvchi (extinguisher)", 220_000,
         "https://images.unsplash.com/photo-1572196410033-2bd00d3a6a87",
         "https://www.aliexpress.com/wholesale-mini-fire-extinguisher-car.html", "Aliexpress"),
        ("UV himoyali ko'zoynak", 195_000,
         "https://images.unsplash.com/photo-1577803645773-f96470509666",
         "https://www.aliexpress.com/wholesale-uv400-sunglasses-hiking.html", "Aliexpress"),
        ("Acil radiotelefon (walkie-talkie 2x)", 380_000,
         "https://images.unsplash.com/photo-1517336714731-489689fd1ca8",
         "https://www.aliexpress.com/wholesale-walkie-talkie-pair.html", "Aliexpress"),
        ("Quyoshdan himoya shapka (boyni qoplaydigan)", 95_000,
         "https://images.unsplash.com/photo-1576188973526-aa7e0530edf9",
         "https://www.aliexpress.com/wholesale-sun-hat-hiking-neck.html", "Aliexpress"),
    ],
}

DESCRIPTIONS = {
    "tent":     "Sifatli material, suv o'tkazmas, tog' iqlimiga moslashtirilgan. CE sertifikatli.",
    "climbing": "Professional alpinizm va arqon ishi uchun. UIAA standartiga muvofiq.",
    "gear":     "Yengil va chidamli — uzoq sayohat uchun ishonchli hamroh.",
    "safety":   "Favqulodda holatlarda hayotni saqlash uchun zarur jihoz. Doimo yoningizda bo'lsin.",
}


class Command(BaseCommand):
    help = "Tog'AI Outdoor — chodir/arqon/sayohat anjomlari (external linklar bilan)"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true",
                            help="Mavjud demo mahsulotlarni o'chirib qaytadan to'ldirish")

    @transaction.atomic
    def handle(self, *args, **opts):
        # Reset — har doim demo seller mahsulotlarini tozalaymiz (kategoriya o'zgargan)
        Product.objects.filter(seller__phone__startswith="+99890000").delete()
        # Eski kategoriyalarni ham (food, herbs, honey, wood, clothing) — endi yo'q
        Category.objects.filter(slug__in=["food", "herbs", "honey", "wood", "clothing"]).delete()

        # 1. Yangi kategoriyalar
        cat_map = {}
        for c in CATEGORIES:
            obj, _ = Category.objects.update_or_create(slug=c["slug"], defaults=c)
            cat_map[c["slug"]] = obj

        # 2. Sotuvchilar
        sellers = []
        for s in SELLERS:
            user, created = User.objects.get_or_create(
                phone=s["phone"],
                defaults={
                    "full_name": s["full_name"],
                    "seller_name": s["seller_name"],
                    "account_type": "seller",
                    "seller_verified": True,
                },
            )
            if not created:
                user.account_type = "seller"
                user.seller_name = s["seller_name"]
                user.seller_verified = True
                user.save(update_fields=["account_type", "seller_name", "seller_verified"])
            sellers.append(user)

        # 3. Mahsulotlar
        total = 0
        for slug, items in PRODUCTS.items():
            cat = cat_map[slug]
            base_desc = DESCRIPTIONS[slug]
            for entry in items:
                title, price, img, ext_url, ext_seller = entry
                seller = random.choice(sellers)
                full_image_url = img
                if "unsplash.com" in img and "?" not in img:
                    full_image_url = f"{img}?auto=format&fit=crop&w=600&q=80"
                discount = None
                if random.random() < 0.5:
                    pct = random.choice([10, 15, 20, 25])
                    discount = Decimal(int(price * (1 - pct / 100) / 1000) * 1000)
                stock = random.randint(5, 80)
                rating = round(random.uniform(4.0, 4.9), 1)
                reviews = random.randint(8, 220)
                is_featured = random.random() < 0.2

                Product.objects.update_or_create(
                    title=title,
                    defaults={
                        "seller": seller,
                        "category": cat,
                        "short_description": base_desc[:200],
                        "description": f"{title}\n\n{base_desc} Tog'AI Bozori orqali sertifikatlangan.",
                        "price": Decimal(price),
                        "discount_price": discount,
                        "stock_quantity": stock,
                        "status": Product.STATUS_ACTIVE,
                        "is_featured": is_featured,
                        "rating": Decimal(str(rating)),
                        "reviews_count": reviews,
                        "ai_generated_description": False,
                        "image_url": full_image_url,
                        "external_url": ext_url,
                        "external_seller": ext_seller,
                    },
                )
                total += 1

        self.stdout.write(self.style.SUCCESS(
            f"Outdoor magazin: {total} mahsulot, {len(cat_map)} kategoriya"
        ))
