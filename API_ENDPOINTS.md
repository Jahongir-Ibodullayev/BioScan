# BioScan Backend — Hamma API endpoint'lari

**Base URL** (production): `https://startup-seven-pied.vercel.app/api/`
**Direct VPS** (HTTP): `http://62.171.185.105:8090/api/`
**Auth**: JWT Bearer token (login endpoint'lardan tashqari)

---

## 🔐 1. AUTH — Foydalanuvchi (Accounts)

| Method | Endpoint | Tavsif | Auth |
|---|---|---|---|
| POST | `/api/auth/quick/` | Tezkor kirish (kod kerak emas — DEBUG rejim) | ❌ |
| POST | `/api/auth/otp/request/` | **APK uchun**: SMS OTP yuborish (Eskiz) | ❌ |
| POST | `/api/auth/otp/verify/` | OTP kodni tekshirish → JWT | ❌ |
| POST | `/api/auth/tg-otp/request/` | **Webapp uchun**: Telegram bot OTP | ❌ |
| POST | `/api/auth/tg-otp/verify/` | Telegram OTP tekshirish → JWT | ❌ |
| POST | `/api/auth/token/refresh/` | Refresh JWT token | ❌ |
| GET | `/api/auth/me/` | Joriy foydalanuvchi profili | ✅ |
| PATCH | `/api/auth/me/` | Profilni yangilash | ✅ |

**Body misollar**:
```json
POST /api/auth/tg-otp/request/
{ "phone": "+998901234567" }

POST /api/auth/tg-otp/verify/
{ "phone": "+998901234567", "code": "123456", "full_name": "Otabek" }
```

---

## 🌿 2. CATALOG — Turlar bazasi (Species)

Hammasi `/api/species/` ostida (DRF ViewSet).

| Method | Endpoint | Tavsif | Auth |
|---|---|---|---|
| GET | `/api/species/` | Barcha turlar (page, search, filter) | ❌ |
| GET | `/api/species/?red_book=true` | Faqat Qizil kitob | ❌ |
| GET | `/api/species/?category=gul` | Kategoriya bo'yicha | ❌ |
| GET | `/api/species/?iucn=CR` | IUCN status'i bo'yicha | ❌ |
| GET | `/api/species/?search=lola` | Qidiruv | ❌ |
| GET | `/api/species/{slug}/` | Bitta tur to'liq ma'lumot | ❌ |

**Filter parametrlari**: `red_book`, `category`, `iucn`, `is_medicinal`, `is_honey_plant`, `is_edible`, `livestock_danger`, `halal_status`, `search`, `page`, `page_size`

---

## 🔬 3. OBSERVATIONS — Kuzatuvlar (Skanlar)

| Method | Endpoint | Tavsif | Auth |
|---|---|---|---|
| GET | `/api/observations/` | Foydalanuvchi kuzatuvlari | ✅ |
| POST | `/api/observations/` | Yangi kuzatuv | ✅ |
| GET | `/api/observations/{id}/` | Bitta kuzatuv | ✅ |
| DELETE | `/api/observations/{id}/` | O'chirish | ✅ |
| **POST** | **`/api/observations/scan/`** | **AI skan — rasm yuborish** (multipart) | ❌* |
| GET | `/api/observations/public/` | Global GPS-tagged kuzatuvlar (xarita) | ❌ |
| GET | `/api/observations/yearbook/?year=2026` | Yillik PDF kitob | ✅ |

**Scan endpoint'i**:
```
POST /api/observations/scan/
Content-Type: multipart/form-data

photo: <file>
lat: 41.3275 (optional)
lng: 69.2089 (optional)
```

Javob:
```json
{
  "identified": true,
  "species": {
    "slug": "alhagi-pseudalhagi",
    "name": "Yantoq",
    "latin": "Alhagi pseudalhagi",
    "summary": "...",
    "description": "...",
    "habitat": "...",
    "uses": "...",
    "warnings": "...",
    "first_aid": "...",
    "red_book": false,
    "iucn_status": "LC",
    "alternatives": [...]
  },
  "confidence": 0.92,
  "observation_id": 123,
  "new_species": false
}
```

---

## 💬 4. CHAT — AI suhbat

| Method | Endpoint | Tavsif | Auth |
|---|---|---|---|
| GET | `/api/chat/conversations/` | Foydalanuvchi suhbatlari ro'yxati | ✅ |
| POST | `/api/chat/conversations/` | Yangi suhbat | ✅ |
| GET | `/api/chat/conversations/{id}/` | Suhbat tarixi | ✅ |
| POST | `/api/chat/conversations/{id}/messages/` | Yangi xabar yuborish | ✅ |
| POST | `/api/chat/ai/` | **Anonim AI savol** (auth kerak emas) | ❌ |

**AI public**:
```json
POST /api/chat/ai/
{ "message": "Yantoq tikan ostidan o'sgan o'simlikni qanday tanish kerak?" }

→ { "reply": "Yantoq tikani — ..." }
```

---

## 🔍 5. SEARCH — Qidiruv (External APIs)

| Method | Endpoint | Tavsif | Auth |
|---|---|---|---|
| GET | `/api/search/taxa/?q=lola&per_page=10&locale=uz` | iNaturalist + AI tarjima qidiruv | ❌ |
| GET | `/api/search/taxa/{taxon_id}/` | iNat tur tafsiloti | ❌ |
| GET | `/api/search/observations/?taxon_id=X&lat=Y&lng=Z&radius=500` | Yaqin atrofdagi kuzatuvlar | ❌ |
| GET | `/api/search/wiki/?title=Yantoq&lang=uz` | Wikipedia tavsif | ❌ |
| GET | `/api/search/browse/?per_page=50&category=plant&place=uz` | Qidiruv'ning katalog versiyasi | ❌ |
| GET | `/api/search/gbif/?q=Tulipa` | GBIF tur qidiruvi | ❌ |
| GET | `/api/search/gbif/{taxon_key}/` | GBIF tafsiloti | ❌ |
| GET | `/api/search/gbif/occurrences/?taxon_key=X` | GBIF kuzatuvlar | ❌ |
| POST | `/api/search/enrich/` | AI bilan tur ma'lumotini boyitish | ✅ |
| POST | `/api/search/ai-help/` | AI tibbiy/biologik savol-javob | ✅ |

---

## 🛍 6. SHOP — Magazin

| Method | Endpoint | Tavsif | Auth |
|---|---|---|---|
| GET | `/api/shop/categories/` | Kategoriyalar | ❌ |
| GET | `/api/shop/categories/{slug}/` | Bitta kategoriya | ❌ |
| GET | `/api/shop/products/` | Mahsulotlar (filter: category, price, brand, search) | ❌ |
| GET | `/api/shop/products/{slug}/` | Bitta mahsulot to'liq | ❌ |
| POST | `/api/shop/products/{slug}/ai-generate/` | AI tavsifi yaratish | ✅ |
| **GET** | `/api/shop/seller/products/` | Sotuvchi mahsulotlari | ✅ (seller) |
| POST | `/api/shop/seller/products/` | Yangi mahsulot qo'shish | ✅ (seller) |
| PATCH | `/api/shop/seller/products/{id}/` | Mahsulot yangilash | ✅ (seller) |
| **GET** | `/api/shop/cart/` | Savatcha | ✅ |
| POST | `/api/shop/cart/` | Savatchaga qo'shish | ✅ |
| POST | `/api/shop/cart/update/` | Soni o'zgartirish | ✅ |
| POST | `/api/shop/cart/{id}/remove/` | Savatchadan olib tashlash | ✅ |
| POST | `/api/shop/cart/clear/` | Savatchani bo'shatish | ✅ |
| **GET** | `/api/shop/orders/` | Buyurtmalar tarixi | ✅ |
| POST | `/api/shop/orders/` | Yangi buyurtma berish | ✅ |
| GET | `/api/shop/orders/{order_number}/` | Bitta buyurtma | ✅ |
| **GET** | `/api/shop/wishlist/` | Sevimli mahsulotlar | ✅ |
| POST | `/api/shop/wishlist/` | Sevimliga qo'shish | ✅ |
| DELETE | `/api/shop/wishlist/{id}/` | Sevimlidan olib tashlash | ✅ |
| **GET** | `/api/shop/reviews/?product={slug}` | Mahsulot sharhlari | ❌ |
| POST | `/api/shop/reviews/` | Yangi sharh | ✅ |

---

## 💾 7. COLLECTIONS — Saqlangan turlar

| Method | Endpoint | Tavsif | Auth |
|---|---|---|---|
| GET | `/api/collections/` | Saqlangan turlar ro'yxati | ✅ |
| POST | `/api/collections/` | Saqlash | ✅ |
| GET | `/api/collections/{id}/` | Bitta saqlangan tur | ✅ |
| DELETE | `/api/collections/{id}/` | O'chirish | ✅ |
| PATCH | `/api/collections/{id}/` | Eslatma yangilash | ✅ |

---

## 🚨 8. INCIDENTS — Hodisalar (xavf, ilon chaqishi)

| Method | Endpoint | Tavsif | Auth |
|---|---|---|---|
| GET | `/api/incidents/` | Hodisalar ro'yxati | ✅ |
| POST | `/api/incidents/` | Yangi hodisa qaydnomasi | ✅ |
| GET | `/api/incidents/{id}/` | Bitta hodisa | ✅ |

---

## 🗺 9. MAP — Xarita markerlari

| Method | Endpoint | Tavsif | Auth |
|---|---|---|---|
| GET | `/api/map/markers/` | Xarita markerlari (xavf zonalari) | ❌ |
| POST | `/api/map/markers/` | Yangi marker | ✅ |
| GET | `/api/map/markers/{id}/` | Bitta marker | ❌ |

---

## 🤖 10. BOT — Telegram webhook

| Method | Endpoint | Tavsif | Auth |
|---|---|---|---|
| POST | `/api/bot/webhook/` | Telegram bot webhook receiver | Telegram |

---

## 🩺 11. HEALTH & DOCS

| Method | Endpoint | Tavsif | Auth |
|---|---|---|---|
| GET | `/api/health/` | Server holatini tekshirish | ❌ |
| GET | `/api/schema/` | OpenAPI sxema (drf-spectacular) | ❌ |
| GET | `/api/docs/` | Swagger UI (interaktiv API hujjati) | ❌ |

---

## 📊 Statistika

| Bo'lim | Endpoint soni |
|---|---|
| Auth | 8 |
| Catalog | 6 (filter variantlari bilan ko'p) |
| Observations | 7 |
| Chat | 5 |
| Search | 10 |
| Shop | ~20 |
| Collections | 5 |
| Incidents | 3 |
| Map | 3 |
| Bot/Health | 4 |
| **JAMI** | **~70+ endpoint** |

---

## 🔑 Auth header

Login bo'lgandan keyin har bir authenticated so'rovga:
```
Authorization: Bearer <access_token>
```

Token muddati: **6 soat** (refresh — 30 kun).

---

## 🌍 CORS

Hozir `CORS_ALLOW_ALL=True` — har qanday domen'dan ishlatish mumkin.

---

## 📝 Filter / Pagination

DRF default — `?page=1&page_size=20`. Maksimum 100.
Search — DRF SearchFilter, `?search=keyword`.

---

## 🧪 Quick test

```bash
# Health check
curl https://startup-seven-pied.vercel.app/api/health/

# Catalog (Qizil kitob, gul)
curl 'https://startup-seven-pied.vercel.app/api/species/?red_book=true&category=gul'

# Bitta tur
curl https://startup-seven-pied.vercel.app/api/species/tulipa-greigii/

# Shop
curl 'https://startup-seven-pied.vercel.app/api/shop/products/?per_page=10'

# Public observations (xarita uchun)
curl https://startup-seven-pied.vercel.app/api/observations/public/

# Telegram OTP request
curl -X POST -H "Content-Type: application/json" \
  -d '{"phone":"+998901234567"}' \
  https://startup-seven-pied.vercel.app/api/auth/tg-otp/request/
```
