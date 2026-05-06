# Tog'AI E-Commerce — Texnik Vazifa

## 1. Maqsad

Tog'AI ekosistemasi ichida **tabiat sevuvchilar uchun bozor** — sayohat anjomlari, dorivor giyohlar, asal, yog'och, mahalliy hunarmandchilik mahsulotlari. AI yordamida tavsif yaratish va Tog'AI catalog turlari bilan bog'lash imkoniyati.

## 2. Foydalanuvchi rollari

| Rol | Imkoniyatlari |
|-----|--------------|
| **Customer** (default) | Mahsulot ko'rish, savatcha, buyurtma, sevimlilar, sharh |
| **Seller** | + Mahsulot CRUD, AI tavsif, savdo statistikasi |
| **Super admin** | + Hamma sotuvchi va mahsulotlarni boshqarish |

`accounts.User.account_type` orqali. Standart — `customer`. Sotuvchi bo'lish uchun foydalanuvchi `/api/auth/become-seller/` ga so'rov yuboradi (admin tasdiqlaydi yoki avtomatik).

## 3. Ma'lumotlar bazasi

```
Category (slug, name, parent → daraxt struktura, image)
   ↓
Product (seller, category, title, price, stock, status, ai_generated)
   ↓
ProductImage (rasmlar — bir nechta)

Cart (user 1:1) → CartItem (product, quantity)

Order (customer, status, total) → OrderItem (snapshot title+price)

Wishlist (user, product) — sevimlilar
Review (product, user, rating 1-5, comment)
```

**Muhim narsalar**:
- `OrderItem.title_snapshot` va `price_snapshot` — buyurtma vaqtidagi ma'lumotni saqlaydi (sotuvchi narxni keyinroq o'zgartirsa, eski buyurtma o'zgarmaydi)
- `Product.related_species` → `catalog.Species` — mahsulotni tabiat turi bilan bog'lash (Yantoq → Yantoqdan asal)
- `Order.shipping_cost` 200K+ buyurtmada bepul

## 4. API Endpoints

### Public (auth shart emas)
```
GET  /api/shop/categories/              — kategoriyalar
GET  /api/shop/products/                — mahsulotlar (filterlar: category, q, featured)
GET  /api/shop/products/{id}/           — bitta mahsulot
GET  /api/shop/reviews/?product=X       — sharhlar
```

### Seller (auth + account_type=seller)
```
GET    /api/shop/seller/products/                — o'z mahsulotlari
POST   /api/shop/seller/products/                — yangi mahsulot
PUT    /api/shop/seller/products/{id}/           — yangilash
DELETE /api/shop/seller/products/{id}/           — o'chirish
POST   /api/shop/seller/products/{id}/ai-generate/ — AI tavsif (Groq Llama 3.3)
```

### Customer (auth)
```
GET  /api/shop/cart/                    — savatcha
POST /api/shop/cart/add/                — {product_id, quantity}
POST /api/shop/cart/update/             — {item_id, quantity}
POST /api/shop/cart/clear/              — savatni tozalash

GET  /api/shop/orders/                  — buyurtmalarim
POST /api/shop/orders/checkout/         — buyurtma berish (savat → order)
GET  /api/shop/orders/{id}/             — bitta buyurtma

GET    /api/shop/wishlist/              — sevimlilar
POST   /api/shop/wishlist/              — sevimliga qo'sh
DELETE /api/shop/wishlist/{id}/         — olib tashlash

POST /api/shop/reviews/                 — yangi sharh
```

## 5. AI Integration

`POST /api/shop/seller/products/{id}/ai-generate/`:

Sotuvchi mahsulot yaratganda, `description` bo'sh bo'lsa, ushbu endpoint Groq LLM (llama-3.3-70b) orqali avtomatik tavsif yaratadi:

**Prompt**: O'zbek tilida, 3-5 jumla, SEO-friendly, foyda va xususiyatlarni ta'kidlaydi.

**Throttle**: `AIChatThrottle` (20/min). Sotuvchi qaytarib bosolmasin.

## 6. Xavfsizlik

| Tahdid | Yechim |
|--------|--------|
| Boshqa sotuvchining mahsulotini o'zgartirish | `IsSellerOrReadOnly` permission + `seller=request.user` filter |
| Yetarli bo'lmagan stock'ni sotish | `checkout()` da `transaction.atomic` + stock validation |
| Eski narx bo'yicha buyurtma | `OrderItem.price_snapshot` saqlash |
| Bot orqali AI tavsif spam | `AIChatThrottle` 20/min |
| Mahsulot egasi narxini buyurtmadan keyin o'zgartirsa | `OrderItem.title_snapshot` |
| To'lov xavfsizligi | Click/Payme integratsiyasi keyingi bosqichda |

## 7. Bozor logikasi

1. Mahsulot **draft** holatda yaratiladi → sotuvchi tahrirlaydi → **active** qiladi
2. Stock 0 ga tushsa avtomatik **out_of_stock** (todo: signal qo'shish)
3. `is_featured` admin tomonidan o'rnatiladi (asosiy sahifada chiqadi)
4. Sharh — faqat 1 marta bir mahsulot uchun (`unique_together`)
5. Reyting har sharhda hisoblanadi (avg of all reviews)

## 8. Frontend integratsiya

- **Bottom nav** da Q.Kitob → **Magazin** ga o'zgartirildi
- `/app/shop` — bosh sahifa: kategoriyalar + tavsiya qilingan + AI yordamchi
- `/app/shop/cart` — savatcha
- `/app/shop/product/{id}` — mahsulot batafsil
- `/app/shop/sell` — sotuvchi panel (todo: yangi sahifa)
- Cart count `localStorage` da keshlanadi (offline ko'rsatish)

## 9. Migratsiya buyrug'i

```bash
python manage.py makemigrations accounts shop
python manage.py migrate
python manage.py createsuperuser  # admin yaratish
```

`accounts` app'iga `account_type` field qo'shildi — User schema migratsiya talab qiladi.

## 10. Bosqichma-bosqich roadmap

- [x] Phase 1: Models + Serializers + Views + URLs (tayyor)
- [x] Phase 2: Public catalog API (tayyor)
- [x] Phase 3: Cart + Order + Checkout (tayyor)
- [x] Phase 4: AI description generator (tayyor)
- [ ] Phase 5: Frontend ShopPage (qisman, placeholder)
- [ ] Phase 6: Seller dashboard sahifa
- [ ] Phase 7: Click/Payme to'lov integratsiyasi
- [ ] Phase 8: Yetkazib berish — Yandex Delivery / o'z xizmati
- [ ] Phase 9: Push notification (Telegram bot orqali — buyurtma holati)

## 11. Test ma'lumotlari

```bash
# Kategoriyalar yaratish
python manage.py shell
>>> from shop.models import Category
>>> Category.objects.create(name="Sayohat anjomlari", slug="gear")
>>> Category.objects.create(name="Dorivor giyohlar", slug="herbs")
>>> Category.objects.create(name="Asal va shifoli mahsulotlar", slug="honey")
```

## 12. Statistika va monitoring

- `Product.views_count` — har detail view'da +1
- `Product.sales_count` — checkout vaqtida +quantity
- `Product.rating` + `reviews_count` — har sharhda yangilanadi
- Admin panelda hammasi ko'rinadi
