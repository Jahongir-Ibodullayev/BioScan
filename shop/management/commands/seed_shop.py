"""
Tog'AI Magazin: 100+ mahsulot bilan to'ldirish.

Generik tog'/sayohat/tabiat mahsulotlari — Uzum yoki Uzbek brendlardan
foydalanmaydi. Rasmlar Unsplash dan (CC0) yoki Pexels dan.

Foydalanish:
  python manage.py seed_shop          # standart 100+ mahsulot
  python manage.py seed_shop --reset  # avval o'chirib, keyin to'ldirish
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
# Kategoriyalar — frontend FALLBACK_CATEGORIES bilan moslashgan
# ============================================================
CATEGORIES = [
    {"name": "Tog' kiyimlari",     "slug": "clothing", "order": 1},
    {"name": "Sayohat anjomlari",  "slug": "gear",     "order": 2},
    {"name": "Dorivor giyohlar",   "slug": "herbs",    "order": 3},
    {"name": "Asal va shifoli",    "slug": "honey",    "order": 4},
    {"name": "Yog'och buyumlar",   "slug": "wood",     "order": 5},
    {"name": "Tabiiy ovqat",       "slug": "food",     "order": 6},
]

# ============================================================
# Sotuvchilar — bir nechta demo seller (ehtiyojga qarab)
# ============================================================
SELLERS = [
    {"phone": "+998900000001", "full_name": "Tog' Bozori", "seller_name": "Tog' Bozori"},
    {"phone": "+998900000002", "full_name": "Chimgan Trail", "seller_name": "Chimgan Trail"},
    {"phone": "+998900000003", "full_name": "Tabiat Ustozi", "seller_name": "Tabiat Ustozi"},
    {"phone": "+998900000004", "full_name": "Ona Asal", "seller_name": "Ona Asal"},
    {"phone": "+998900000005", "full_name": "Tog' Hunarmandi", "seller_name": "Tog' Hunarmandi"},
]

# ============================================================
# Mahsulotlar shabloni — kategoriya bo'yicha
# Har biriga: title, price (so'm), image (Unsplash CC0)
# ============================================================
PRODUCTS = {
    "clothing": [
        ("Tog' kurtkasi — yengil, suv o'tkazmas", 480_000, "https://images.unsplash.com/photo-1551488831-00ddcb6c6bd3"),
        ("Issiq fleece sviter", 220_000, "https://images.unsplash.com/photo-1591047139829-d91aecb6caea"),
        ("Termo ichki kiyim — qishki", 165_000, "https://images.unsplash.com/photo-1556905055-8f358a7a47b2"),
        ("Tog' shimi — strech, suv qaytaruvchi", 380_000, "https://images.unsplash.com/photo-1473966968600-fa801b869a1a"),
        ("Yengil qishki shapka", 75_000, "https://images.unsplash.com/photo-1576188973526-aa7e0530edf9"),
        ("Issiq qo'lqop — hayvon teri qoplangan", 140_000, "https://images.unsplash.com/photo-1483985988355-763728e1935b"),
        ("Suv o'tkazmas yomg'ir poncho", 95_000, "https://images.unsplash.com/photo-1496318447583-f524534e9ce1"),
        ("Tog' shoxli salla — jun", 180_000, "https://images.unsplash.com/photo-1520975954732-35dd22299614"),
        ("Bog'lanadigan kuchli qator etiklar", 620_000, "https://images.unsplash.com/photo-1542838132-92c53300491e"),
        ("Yengil yozgi etiklar", 350_000, "https://images.unsplash.com/photo-1542291026-7eec264c27ff"),
        ("Termal jurabchalar (3 juft)", 85_000, "https://images.unsplash.com/photo-1586350977771-2a1dc9beafe3"),
        ("Quyosh ochkilari — UV himoyali", 240_000, "https://images.unsplash.com/photo-1577803645773-f96470509666"),
        ("Yangi yog'di qaytaruvchi ko'zoynak", 195_000, "https://images.unsplash.com/photo-1572635196237-14b3f281503f"),
        ("Yengil jacket — ko'klam-kuz", 410_000, "https://images.unsplash.com/photo-1551537482-f2075a1d41f2"),
        ("Bahor yomg'ir kurtkasi", 295_000, "https://images.unsplash.com/photo-1591195853828-11db59a44f6b"),
    ],
    "gear": [
        ("Tog' tasmali ryukzak 60L", 750_000, "https://images.unsplash.com/photo-1553062407-98eeb64c6a62"),
        ("Yengil sayohat ryukzaki 30L", 420_000, "https://images.unsplash.com/photo-1622560480605-d83c853bc5c3"),
        ("Suv qoplari — ichish nayli bilan", 115_000, "https://images.unsplash.com/photo-1559827260-dc66d52bef19"),
        ("Termal flyaga 750ml", 130_000, "https://images.unsplash.com/photo-1602143407151-7111542de6e8"),
        ("4 kishilik chodir — yengil", 950_000, "https://images.unsplash.com/photo-1504280390367-361c6d9f38f4"),
        ("2 kishilik tog' chodir", 680_000, "https://images.unsplash.com/photo-1487730116645-74489c95b41b"),
        ("Tog' uxlash xaltasi -10°C", 540_000, "https://images.unsplash.com/photo-1496080174650-637e3f22fa03"),
        ("Yengil sayohat gilamchasi", 180_000, "https://images.unsplash.com/photo-1571687949921-1306bfb24b72"),
        ("Quyosh batareyali fonar", 220_000, "https://images.unsplash.com/photo-1507525428034-b723cf961d3e"),
        ("Bosh fonar LED — 600 lumen", 165_000, "https://images.unsplash.com/photo-1551415923-a2297c7fda79"),
        ("Multi-asbob (Leatherman tipi)", 380_000, "https://images.unsplash.com/photo-1574870111867-089730e5a72b"),
        ("Sayohat pichoq — qonun ruxsat etgan", 240_000, "https://images.unsplash.com/photo-1593504049359-74330189a345"),
        ("Tog' tayoq — telescope", 195_000, "https://images.unsplash.com/photo-1551632811-561732d1e306"),
        ("Tashqi power-bank 20000mAh", 290_000, "https://images.unsplash.com/photo-1609592424823-58a5e0e6ca9e"),
        ("Mini gaz pechka (sayohat)", 225_000, "https://images.unsplash.com/photo-1517483000871-1dbf64a6e1c6"),
        ("Sayohat oshxona qozon-tovasi", 285_000, "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136"),
        ("Suv tozalovchi filtr 100L", 320_000, "https://images.unsplash.com/photo-1560089165-5b96a6ed4b1c"),
        ("Termo qopqoqli stakan 350ml", 95_000, "https://images.unsplash.com/photo-1485808191679-5f86510681a2"),
        ("Yong'in chaqirish o'choqi (firestarter)", 78_000, "https://images.unsplash.com/photo-1517398741578-6cf8b62b95cf"),
        ("Sayohat birinchi yordam to'plami", 145_000, "https://images.unsplash.com/photo-1603398938378-e54eab446dde"),
    ],
    "herbs": [
        ("Yantoq quritilgan choy 100g", 35_000, "https://images.unsplash.com/photo-1558160074-4d7d8bdf4256"),
        ("Yalpiz quruq barg 50g", 25_000, "https://images.unsplash.com/photo-1628557044797-f21a177c37ec"),
        ("Sedana urug'i — sof 200g", 48_000, "https://images.unsplash.com/photo-1599909366516-6c1d3a01d99c"),
        ("Isiriq quruq 30g", 22_000, "https://images.unsplash.com/photo-1564982752979-3f7bc974d29a"),
        ("Choboq giyoh 100g", 32_000, "https://images.unsplash.com/photo-1597305877032-0668b3c6413a"),
        ("Tog' chetki choy aralashma", 65_000, "https://images.unsplash.com/photo-1576092768241-dec231879fc3"),
        ("Shifobaxsh ildiz to'plam", 85_000, "https://images.unsplash.com/photo-1564890369478-c89ca6d9cde9"),
        ("Lavanda quruq gul 50g", 42_000, "https://images.unsplash.com/photo-1585670210693-46b27e8ea0ce"),
        ("Romashka choy 100g", 28_000, "https://images.unsplash.com/photo-1594631252845-29fc4cc8cde9"),
        ("Tog' rayhon (oregano) 50g", 30_000, "https://images.unsplash.com/photo-1466637574441-749b8f19452f"),
        ("Yer yong'oq mevalari (qadimgi nav)", 38_000, "https://images.unsplash.com/photo-1583692331507-fc0bbabb7add"),
        ("Burgan barg quruq", 32_000, "https://images.unsplash.com/photo-1612203985729-70726954388c"),
        ("Tugay shifoli choy", 58_000, "https://images.unsplash.com/photo-1562525019-c0c4ad12f5a3"),
        ("Achchiq shuvoq 50g", 26_000, "https://images.unsplash.com/photo-1510626176961-4b57d4fbad03"),
        ("Sariq giyoh shifoli", 45_000, "https://images.unsplash.com/photo-1559059699-085698eba48c"),
    ],
    "honey": [
        ("Tog' asali — sof, 500g", 120_000, "https://images.unsplash.com/photo-1587049352846-4a222e784d38"),
        ("Bahor asali 1kg", 215_000, "https://images.unsplash.com/photo-1536788558790-86bbf17b3eaa"),
        ("Akatsiya asali — tiniq, 700g", 175_000, "https://images.unsplash.com/photo-1597016087305-8e0e2c5b3a31"),
        ("Tog' asali — sutli aralash 500g", 145_000, "https://images.unsplash.com/photo-1582284540020-8acbe03f4924"),
        ("Asal chuvalchang xona — 250g", 95_000, "https://images.unsplash.com/photo-1527685609591-44b0aef2400f"),
        ("Propolis tinktura 50ml", 85_000, "https://images.unsplash.com/photo-1608797178974-15b35a64ede9"),
        ("Asal mumi sham (hand-made)", 65_000, "https://images.unsplash.com/photo-1607344645866-009c320c5ab0"),
        ("Asalari oligozaxar 30 kapsula", 290_000, "https://images.unsplash.com/photo-1576092762791-dd9e2220abd1"),
        ("Asalli yong'oq 400g", 110_000, "https://images.unsplash.com/photo-1571115764595-644a1f56a55c"),
        ("Asalli kalla yong'oq 250g", 80_000, "https://images.unsplash.com/photo-1569288063610-23d7d1b9eedc"),
        ("Tog' asali siroq 1.5kg", 320_000, "https://images.unsplash.com/photo-1490554932995-4ad9eb4ddeed"),
        ("Asal va atirgul mahsulot 200g", 65_000, "https://images.unsplash.com/photo-1571115764595-644a1f56a55c"),
    ],
    "wood": [
        ("Yog'och tovoq — qayin", 85_000, "https://images.unsplash.com/photo-1606767341197-bd0d3a8a9f76"),
        ("Yog'och kosa — o'rik", 65_000, "https://images.unsplash.com/photo-1611066516083-0b8a8e87a96e"),
        ("Sayohat yog'och qoshiq to'plami (3)", 45_000, "https://images.unsplash.com/photo-1528820324996-5acdf8e167bf"),
        ("Yog'och tashqi pichoq sopi", 95_000, "https://images.unsplash.com/photo-1604948501466-4e9c339b9c24"),
        ("Tog' yog'ochidan o'tlash taxtasi", 145_000, "https://images.unsplash.com/photo-1608686207856-001b95cf60ca"),
        ("Hand-made yog'och soat", 320_000, "https://images.unsplash.com/photo-1517336714731-489689fd1ca8"),
        ("Yog'och sham o'rni (3 sham)", 110_000, "https://images.unsplash.com/photo-1601925268574-ad7af89a93cb"),
        ("Hunarmandlik yog'och tasbeh", 75_000, "https://images.unsplash.com/photo-1606722590583-6951b5ea92ad"),
        ("Yog'och fanali tutqich", 55_000, "https://images.unsplash.com/photo-1567113463300-102a7eb3cb26"),
        ("Eman daraxti tutqichli oyna", 280_000, "https://images.unsplash.com/photo-1600585154340-be6161a56a0c"),
        ("Yog'och dam olish kursi (mini)", 480_000, "https://images.unsplash.com/photo-1567538096630-e0c55bd6374c"),
        ("Hunarmandlik yog'och brelok", 28_000, "https://images.unsplash.com/photo-1593696140826-c58b021acf8b"),
    ],
    "food": [
        ("Quruq mevalar to'plam 500g", 75_000, "https://images.unsplash.com/photo-1604908554161-3cf04d56a5fb"),
        ("Tog' yong'og'i 1kg (qadimiy nav)", 145_000, "https://images.unsplash.com/photo-1599639957043-f3aa5c986398"),
        ("Quruq o'rik 500g", 65_000, "https://images.unsplash.com/photo-1603833665858-e61d17a86224"),
        ("Quruq olxo'ri 500g", 58_000, "https://images.unsplash.com/photo-1597305877032-0668b3c6413a"),
        ("Pista — natural 400g", 185_000, "https://images.unsplash.com/photo-1599629954294-14df9ec8bc15"),
        ("Bodom — Markaziy Osiyo 500g", 165_000, "https://images.unsplash.com/photo-1508061253366-f7da158b6d46"),
        ("Mavj quruq mevasi 250g", 42_000, "https://images.unsplash.com/photo-1587049352846-4a222e784d38"),
        ("Tabiiy yong'oq yog'i 500ml", 95_000, "https://images.unsplash.com/photo-1474722883778-792e7990302f"),
        ("Sezam (kunjit) 300g", 38_000, "https://images.unsplash.com/photo-1606312619070-d48b4c652a52"),
        ("Yashil choy — Markaziy Osiyo 200g", 55_000, "https://images.unsplash.com/photo-1576092768241-dec231879fc3"),
        ("Qora choy ekstra 250g", 48_000, "https://images.unsplash.com/photo-1571934811356-5cc061b6821f"),
        ("Yong'oq + asal energiya bar (10)", 85_000, "https://images.unsplash.com/photo-1571115764595-644a1f56a55c"),
        ("Xushbo'y ziravor to'plam", 120_000, "https://images.unsplash.com/photo-1596040033229-a9821ebd058d"),
        ("Tutqun (granat) suvi 500ml", 35_000, "https://images.unsplash.com/photo-1611077861316-0d52e7e0a6c9"),
        ("Tog' dukkagidoshlar to'plami 1kg", 95_000, "https://images.unsplash.com/photo-1606312619070-d48b4c652a52"),
        ("Quritilgan choy olma 200g", 32_000, "https://images.unsplash.com/photo-1568901346375-23c9450c58cd"),
    ],
}

DESCRIPTIONS = {
    "clothing": "Tog' iqlimiga moslashtirilgan, sifatli material. O'zbekiston tog'larida sinov qilingan.",
    "gear":     "Yengil va chidamli — uzoq sayohat uchun ishonchli hamroh. CE sertifikatli.",
    "herbs":    "Mahalliy fermerlardan to'plangan, ekologik toza. Quyosh ostida quritilgan.",
    "honey":    "100% sof — qo'shimchalarsiz. Tog' gullari va dorivor giyohlardan yig'ilgan.",
    "wood":     "Hand-made — mahalliy hunarmandlar tomonidan tayyorlangan. Tabiiy yog' bilan ishlov berilgan.",
    "food":     "Konservant qo'shilmagan, tabiiy mahsulot. Markaziy Osiyo iqlimiga xos.",
}


class Command(BaseCommand):
    help = "Tog'AI Magazinni 100+ generik mahsulot bilan to'ldiradi"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Mavjud mahsulotlarni o'chirib qaytadan to'ldirish")

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts.get("reset"):
            deleted = Product.objects.filter(seller__phone__startswith="+99890000").delete()
            self.stdout.write(self.style.WARNING(f"O'chirildi: {deleted}"))

        # 1. Kategoriyalar
        cat_map = {}
        for c in CATEGORIES:
            obj, _ = Category.objects.get_or_create(slug=c["slug"], defaults=c)
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

        # 3. Mahsulotlar — har bir kategoriyadan
        total = 0
        for slug, items in PRODUCTS.items():
            cat = cat_map[slug]
            base_desc = DESCRIPTIONS[slug]
            for title, price, image_url in items:
                seller = random.choice(sellers)
                # Tasodifiy chegirma 10-30% (60% mahsulotlarda)
                discount = None
                if random.random() < 0.6:
                    pct = random.choice([10, 15, 20, 25, 30])
                    discount = Decimal(int(price * (1 - pct / 100) / 1000) * 1000)
                stock = random.randint(5, 80)
                rating = round(random.uniform(3.8, 4.9), 1)
                reviews = random.randint(3, 220)
                is_featured = random.random() < 0.15

                Product.objects.update_or_create(
                    title=title,
                    defaults={
                        "seller": seller,
                        "category": cat,
                        "short_description": base_desc[:200],
                        "description": f"{title}\n\n{base_desc} Sifat va narx muvozanati — Tog'AI Bozori orqali tasdiqlangan.",
                        "price": Decimal(price),
                        "discount_price": discount,
                        "stock_quantity": stock,
                        "status": Product.STATUS_ACTIVE,
                        "is_featured": is_featured,
                        "rating": Decimal(str(rating)),
                        "reviews_count": reviews,
                        "ai_generated_description": False,
                    },
                )
                total += 1

        self.stdout.write(self.style.SUCCESS(
            f"Tog'AI Magazin to'ldirildi: {total} mahsulot, "
            f"{len(cat_map)} kategoriya, {len(sellers)} sotuvchi"
        ))
