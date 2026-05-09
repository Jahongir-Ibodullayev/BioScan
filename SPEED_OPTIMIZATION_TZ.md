# 🚀 BioScan — Backend → Flutter APK tezlik optimizatsiyasi TZ

**Sana:** 2026-05-09
**Maqsad:** APK ichida har sahifa **<1 soniyada** ko'rinishi (hozir 2-5s)
**Muallif:** Backend va Flutter codebase live diagnostikasi asosida

---

## 0. ⏱️ HOZIRGI HOLAT — real o'lchov

Toshkent client → `https://bioscan.duckdns.org/api/...` (server: `62.171.185.105`, Germaniya, Contabo VPS):

| Phase | Vaqt |
|---|---|
| DNS lookup | 20 ms ✓ |
| TCP handshake | 180 ms |
| TLS handshake | 200 ms |
| **Server TTFB** | **440-1000 ms ⚠️** |
| Total cold request | **~1.7 s ⚠️** |
| Total warm (keep-alive) | ~500 ms |

**Endpoint testlari:**
```
GET /api/health/?deep=1   →  470 ms TTFB (cold)
GET /api/species/         →  500 ms TTFB, 9.2 KB → 2.0 KB gzip ✓
GET /api/shop/products/   →  705 ms TTFB, 12 KB → 2.5 KB gzip ✓
GET /api/shop/categories/ →  547 ms TTFB, 561 B
```

**Diagnoz:**
- ✅ Gzip ishlaydi (4.5x compression)
- ✅ HTTP/2 ishlaydi
- ✅ Frontend cache layer (cache_interceptor.dart) yaxshi yozilgan
- ❌ **TTFB 500ms** — Toshkent→Germany ping faqat ~80-100ms, demak server ichida **400ms+ band** turadi
- ❌ **db.sqlite3 ishlatilyapti** (production'da!)
- ❌ HTTP/3 (QUIC) yo'q — TLS handshake 200ms qo'shimcha
- ❌ Cloudflare/edge yo'q — har request VPS gacha 200ms borib keladi
- ❌ Flutter offline-first emas — 1-marta foydalanuvchi APK ochsa, hammasi tarmoq orqali keladi
- ❌ APK to'g'ridan-to'g'ri DDNS (`bioscan.duckdns.org`) — TLS sertifikat har 90 kun yangilanadi, DDNS bepul lekin DNS TTL 60s

**Maqsad metrikalar (real, erishish mumkin):**

| Endpoint | Hozir | Maqsad | Qanday |
|---|---|---|---|
| TTFB (warm) | 500 ms | **80-150 ms** | Postgres + Redis + connection reuse |
| Catalog ochish | 2-3 s | **<300 ms** | Offline SQLite + background revalidate |
| Shop sahifa | 3-4 s | **<500 ms** | Edge CDN + thumbnail aspect-locked |
| 1-marta APK | 5-8 s | **<2 s** | Bundled seed JSON + lazy network |
| Skan AI | 9-12 s | **5-7 s** | Direct VPS, image compress before upload |

---

## 1. 🥇 TIER-1 — eng katta tezlik (kun-1 yopiladi)

### 1.1 SQLite → PostgreSQL (TTFB 500ms → 150ms)

**Muammo:** `db.sqlite3` 520 KB lekin har request `SELECT ...FROM catalog_species` qilmasdan oldin OS file lock kutadi. Concurrent so'rovlarda gevent worker bloklab qoladi.

**Yechim:**
```bash
# VPS ichida
sudo apt install -y postgresql-16
sudo -u postgres createdb togai
sudo -u postgres psql -c "CREATE USER togai WITH PASSWORD '<STRONG>';"
sudo -u postgres psql -c "GRANT ALL ON DATABASE togai TO togai;"
sudo -u postgres psql -c "ALTER ROLE togai SET timezone TO 'Asia/Tashkent';"

# .env
DATABASE_URL=postgresql://togai:<STRONG>@127.0.0.1:5432/togai
```

`settings.py` allaqachon `dj_database_url` ishlatadi va `CONN_MAX_AGE=600` qo'yilgan — to'g'ri. Faqat `.env`'da `DATABASE_URL` qo'yib `python manage.py migrate` + ma'lumotlarni ko'chirish:

```bash
# 1. SQLite'dan dump
python manage.py dumpdata --natural-foreign --natural-primary \
  -e contenttypes -e auth.Permission -e admin.LogEntry \
  -e sessions --indent 2 > /tmp/full.json

# 2. .env'da DATABASE_URL ni qo'yib, postgresga migrate
python manage.py migrate
python manage.py loaddata /tmp/full.json
```

**Kutilgan natija:** TTFB 500ms → 200ms (read-only catalog uchun, Redis cache hit'gacha)

---

### 1.2 Redis cache MAJBURIY yoqilsin (TTFB 200ms → 30ms)

**Muammo:** `settings.py:256` da `REDIS_URL=""` bo'lsa LocMemCache ishlatadi — bu **har gunicorn worker uchun alohida cache** demak. 8 worker → 8 ta isolated cache → cache hit nisbati ~12%.

**Yechim:**
```bash
sudo apt install -y redis-server
sudo systemctl enable --now redis-server
redis-cli ping  # PONG

# .env
REDIS_URL=redis://127.0.0.1:6379/1
```

`catalog/views.py:79` da `cache.get(key)` allaqachon yozilgan — Redis qo'shilsa 8 worker bitta hot cache bo'lib qoladi. Species list 200ms → **5-10ms** (Redis-pickle deserialize).

**Tekshirish:**
```bash
curl -s -o /dev/null -w "%{time_starttransfer}\n" 'https://bioscan.duckdns.org/api/species/'
# 1-marta: ~200ms (DB hit)
# 2-marta: ~30ms (Redis hit) ← bu kerak
```

---

### 1.3 Cloudflare CDN proxy (cold start 1.7s → 300ms)

**Muammo:** `bioscan.duckdns.org` to'g'ridan-to'g'ri VPS'ga ketadi — har Toshkent foydalanuvchisi har request uchun:
- TCP RTT: 180ms
- TLS RTT (3 round-trip): 200ms
- Server TTFB: 500ms
= **~880ms minimum**

Cloudflare prokisi orqali:
- TCP+TLS Toshkent edge POP'da tugatiladi (RTT 10-30ms — Cloudflare Tashkent yoki Almatyda POP bor)
- VPS bilan keep-alive uzun connection (TLS resumption)
- Anonim GET'lar Cloudflare edge'da cache (Cache-Control middleware allaqachon yozilgan!)

**Yechim:**

1. Domain ol — `bioscan.uz` yoki `togai.uz` ($10/yil Namecheap, GoDaddy, Reg.uz). DDNS production'ga **yaramaydi**.

2. Cloudflare bepul plan'ga ulan:
   - DNS: `api.bioscan.uz A 62.171.185.105` — Proxied (orange cloud) ✓
   - SSL/TLS: **Full (strict)**
   - Caching → Configuration → Browser TTL: 1 hour
   - Speed → Optimization: Brotli ON, Early Hints ON
   - Network: HTTP/3 (QUIC) ON, 0-RTT ON, IPv6 ON

3. Cache rule (Page Rule yoki Cache Rules):
   - `api.bioscan.uz/api/species/*` → Cache Everything, Edge TTL 5min
   - `api.bioscan.uz/api/shop/products/*` → Cache Everything, Edge TTL 5min
   - `api.bioscan.uz/api/shop/categories/*` → Cache Everything, Edge TTL 1h
   - `api.bioscan.uz/api/observations/public/*` → Cache Everything, Edge TTL 10min

`togai/middleware.py:EdgeCacheMiddleware` allaqachon `Cache-Control: public, s-maxage=300` qo'yadi — Cloudflare buni hurmat qiladi.

**Diqqat:** `CACHE_KEY` da `Authorization` header bo'lsa cache yo'q (allaqachon shunday yozilgan). Authenticated foydalanuvchilar har vaqt VPS'ga to'g'ridan-to'g'ri boradi.

**Kutilgan natija:** Cache hit anonim GET'larda 30ms (Toshkent edge), cache miss 200ms.

---

### 1.4 Flutter base URL ni `bioscan.uz` ga ko'chirish

```dart
// lib/src/core/api.dart:17-20
const String defaultApiBase = String.fromEnvironment(
  'API_BASE',
  defaultValue: 'https://api.bioscan.uz/api',  // duckdns o'rniga
);
```

So'ngra:
```bash
flutter build apk --release --split-per-abi \
  --dart-define=API_BASE=https://api.bioscan.uz/api
```

---

## 2. 🥈 TIER-2 — keyingi katta yutuqlar

### 2.1 Offline-first SQLite (Drift) — birinchi ochilish 5s → <1s

**Muammo:** Hozir `shared_preferences` faqat token + lastScan saqlaydi. Catalog (96 species), Shop (48 products), Public observations — har APK qaytadan ochilganda tarmoqdan keladi. Birinchi marta ochilsa 5-8s shimmer.

**Yechim — 2 qatlamli:**

**A. APK ichiga seed JSON joylash (mahalliy fallback):**

```yaml
# pubspec.yaml — assets bo'limiga qo'shish
flutter:
  assets:
    - assets/data/seed_species.json   # 96 species snapshot
    - assets/data/seed_shop.json      # 48 product snapshot
    - assets/data/seed_categories.json
```

Build vaqtida CI/CD seed yangilab oladi:
```bash
# scripts/build_seed.sh
curl -s 'https://api.bioscan.uz/api/species/?page_size=200' \
  > "assets/data/seed_species.json"
curl -s 'https://api.bioscan.uz/api/shop/products/?page_size=100' \
  > "assets/data/seed_shop.json"
curl -s 'https://api.bioscan.uz/api/shop/categories/' \
  > "assets/data/seed_categories.json"
flutter build apk --release ...
```

**B. Drift (SQLite ORM) catalog uchun:**

```yaml
dependencies:
  drift: ^2.20.0
  drift_flutter: ^0.2.0
  sqlite3_flutter_libs: ^0.5.24

dev_dependencies:
  drift_dev: ^2.20.0
  build_runner: ^2.4.13
```

Tablitsa skeleton:
```dart
// lib/src/core/db/cache_db.dart
@DriftDatabase(tables: [SpeciesCache, ProductCache, CategoryCache])
class CacheDB extends _$CacheDB {
  CacheDB() : super(_open());
  // Methods: upsertSpecies, allSpecies, searchSpecies(query), markStale, etc.
}
```

`ApiClient.listSpecies` ni shunday o'zgartirish kerak:
```dart
// 1. Drift'dan darhol mahalliy javobni ber (offline UX)
// 2. Tarmoqdan kelgach DB ni yangila + UI'ni yangi snapshot bilan rebuild
```

Bu `cache_interceptor.dart`'dan **kuchliroq** — chunki SharedPreferences JSON serialize/deserialize 50-200ms (96 species), Drift queries 1-5ms.

**Kutilgan natija:** Catalog/Shop sahifa **darhol** ochiladi (0ms shimmer) → ekranda shimmer ko'rinmaydi → yangilanish background'da, foydalanuvchi sezmaydi.

---

### 2.2 Image thumbnail — server-side, weserv.nl o'rniga

**Muammo:** `catalog/serializers.py:8` rasm uchun `images.weserv.nl` ishlatadi. Bu Cloudflare CDN proxy — yaxshi, lekin:
- 3-shaxs servisi (down bo'lsa rasmlar yo'q)
- Har rasm uchun yana 1 ta TLS handshake (mobile bandwidth)
- iNaturalist/Wikipedia URL'larining hammasini convert qilish

**Yechim — variant A (kichik tirishish):** weserv.nl o'rniga Cloudflare Image Resizing (`/cdn-cgi/image/...`) ishlatish — agar Cloudflare oldida bo'lsa:
```python
def _fast_url(raw: str, w: int = 400) -> str:
    return f"https://api.bioscan.uz/cdn-cgi/image/width={w},quality=70,format=webp/{raw}"
```

**Yechim — variant B (kuchli):** Backend server-side thumbnail generate qiladi, bir marta:

```bash
pip install Pillow django-imagekit
```

```python
# catalog/models.py
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill

class Species(models.Model):
    image = models.ImageField(upload_to="species/", null=True, blank=True)
    image_url = models.URLField(blank=True, default="")
    thumbnail_400 = ImageSpecField(
        source="image",
        processors=[ResizeToFill(400, 400)],
        format="WEBP",
        options={"quality": 75},
    )
```

`/media/` endi `nginx` orqali to'g'ridan-to'g'ri serve qilinadi (Django bypass). Cache-Control 1 yil:
```nginx
location /media/ {
    alias /var/www/togai-backend/media/;
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

**Diqqat:** Variant B faqat `image` field uchun. iNaturalist external `image_url` lar weserv.nl da qoladi (Wikipedia license bilan local saqlash to'g'ri emas).

---

### 2.3 Pagination o'rniga "stream" — birinchi ekran tez chiqsin

**Muammo:** `/api/species/?page=1` 20 ta itemni qaytaradi. Lekin foydalanuvchi ekranda faqat 4-6 ta ko'radi. Backend 20 ta serializer ishlatib JSON ni qurib bo'lguncha foydalanuvchi shimmer ko'radi.

**Yechim — A (light list serializer ya'ni hozirgi yondashuv):** ✓ Allaqachon `SpeciesListSerializer` light field'lar bilan, `.only()` qo'yilgan. Yaxshi.

**Yechim — B (cursor pagination + 10 item):**
```python
# settings.py REST_FRAMEWORK
"DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.CursorPagination",
"PAGE_SIZE": 12,  # 20 → 12 (dastlabki ekran tezroq)
```

**Yechim — C (server-sent events / streaming JSON):** Murakkab, fillu nyetlar — keyingi sprint.

---

### 2.4 Image compress before scan upload — skan AI 9s → 5s

**Muammo:** `lib/src/features/scanner/scanner_page.dart:57` `image_picker` rasm to'liq ekran resolution'da yuboradi (3000x4000 = 4-8 MB). Mobile 4G yuborish 5-8 soniya.

**Yechim:**
```dart
// scanner_page.dart — scan'dan oldin
final picked = await picker.pickImage(
  source: ImageSource.camera,
  maxWidth: 1280,        // 3000 → 1280
  maxHeight: 1280,
  imageQuality: 75,      // JPEG 85 → 75 (etarli AI uchun)
);
```

Backend `observations/views.py` — `OPENROUTER_API_KEY` ga 1280px JPEG yetarli (vision model 512x512 ga downscale qiladi baribir).

**Kutilgan natija:** 4 MB → 200 KB → upload 200ms → AI 4-5s → total **5-7s** (hozirgi 9-12s o'rniga).

---

### 2.5 `dio` parallel `Future.wait` — har sahifa boot tezligi

**Muammo:** `home_page.dart`, `shop_page.dart` hozir `setState`'da ketma-ket request qiladi:
```dart
final cats = await api.shopCategories();      // 500ms
final prods = await api.shopProducts();        // 700ms
// total: 1200ms
```

**Yechim:**
```dart
final results = await Future.wait([
  api.shopCategories(),
  api.shopProducts(),
  api.shopProducts(featured: true),
]);
// total: 700ms (parallel)
```

`dio.adapter.maxConnectionsPerHost = 8` allaqachon qo'yilgan — 6 parallel request bemalol ishlaydi.

**Audit kerak fayllar:**
- `lib/src/features/home/home_page.dart`
- `lib/src/features/shop/shop_page.dart`
- `lib/src/features/profile/profile_page.dart`

Har birini ko'rib `await ... await ...` ketma-ket bo'lsa `Future.wait` ga o'tkazish.

---

## 3. 🥉 TIER-3 — fine-tuning

### 3.1 HTTP/3 (QUIC) — TLS handshake 200ms → 0ms

Cloudflare TIER-1.3 da yoqilsa avtomatik HTTP/3 ishlaydi (Flutter `dio` HTTP/2 ishlatadi, 3'ga keyin). Hozircha `dio` HTTP/3 qo'llab-quvvatlamaydi (issue #2089), lekin **2-marta socket** keep-alive bilan 200ms TLS yo'qoladi.

### 3.2 Brotli compression (gzip o'rniga)

Cloudflare avtomatik Brotli qo'llaydi. Origin nginx ham:
```nginx
brotli on;
brotli_types application/json text/css application/javascript;
brotli_comp_level 5;
```
Brotli gzip'dan ~15-20% kichikroq → mobile 3G da sezilarli.

### 3.3 Database indekslar (slow query log dan keyin)

Postgresga ko'chgandan keyin `pg_stat_statements` extension yoqib, sekin so'rovlarni topish kerak:
```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC LIMIT 20;
```

Ehtimol kerak indekslar:
```sql
CREATE INDEX idx_species_red_book ON catalog_species(red_book) WHERE red_book = true;
CREATE INDEX idx_species_category ON catalog_species(category);
CREATE INDEX idx_obs_public_geo ON observations_observation(latitude, longitude, created_at DESC)
  WHERE is_public = true;
CREATE INDEX idx_shop_active_featured ON shop_product(status, is_featured)
  WHERE status = 'active';
CREATE INDEX idx_shop_category ON shop_product(category_id) WHERE status = 'active';
```

### 3.4 `auth/me/` paydo bo'lishini kamaytirish

`api.dart` har sahifa boot da `getUser()` SharedPreferences'dan oqaydi — yaxshi, tarmoq emas. Lekin `cache_interceptor.dart:65` da `^/auth/me/` 10 minut TTL — buni 1 soatga oshirish mumkin (foydalanuvchi profilni tez-tez yangilashtirmaydi).

```dart
MapEntry(RegExp(r'^/auth/me/'), const Duration(hours: 1)),
```

Push notification bilan invalidate qilinadi (FCM topic `user.<id>.profile`).

### 3.5 Stale-while-revalidate "max-stale" auth so'rovlar uchun

Hozirgi `cache_interceptor.dart` faqat anonim GET'larga qo'llaniladi (Authorization header bo'lsa ham bypass emas — kod ko'rib chiqilsin). Bu yaxshi, lekin **shop cart** kabi auth endpointda ham stale-revalidate ishlatilsa: foydalanuvchi sahifani ochsa, oldingi cart darhol ko'rinadi → 200ms keyin yangilanadi.

### 3.6 Sentry sample rate kamaytirish (production)

`settings.py:38` `traces_sample_rate=0.1` — 10% so'rovlarda Sentry instrumentation. Bu har request 5-15ms qo'shadi. Production stable bo'lsa `0.02` (2%) yetarli.

### 3.7 Gunicorn worker tuning

`gunicorn.conf.py` da `workers = cpu*2`, `worker_class=gevent`, `worker_connections=100` — yaxshi sozlangan. Lekin `preload_app=True` faqat **read-only Django app** uchun ishlaydi, agar SQLite'dan PostgreSQL'ga ko'chgandan keyin ham xatosiz qolsa.

`max_requests=2000` ham yaxshi (memory leak prevention).

### 3.8 Gunicorn `--worker-tmp-dir /dev/shm`

Disk I/O dan saqlanish:
```python
# gunicorn.conf.py
worker_tmp_dir = "/dev/shm"  # tmpfs (RAM)
```
Heartbeat fayllari diskga yozilmaydi → 5-10ms har request.

---

## 4. 📋 ALOHIDA — Flutter side checklist

### 4.1 Drift database integration (TIER-2.1)
- [ ] `pubspec.yaml` da `drift`, `sqlite3_flutter_libs` qo'shish
- [ ] `lib/src/core/db/cache_db.dart` schema yozish
- [ ] `SpeciesRepo`, `ShopRepo` qatlami yaratish (network + db birga)
- [ ] APK build da `assets/data/seed_*.json` ni preload + Drift'ga yozish

### 4.2 Image preload — `cached_network_image`'ni manualtune
```dart
// main.dart
await PaintingBinding.instance.imageCache.maximumSizeBytes = 256 * 1024 * 1024; // 256 MB
```

### 4.3 Loading skeleton o'rniga "stale data + revalidate"
Hozir ko'p sahifa shimmer ko'rsatadi 1-2s. Drift integratsiyasidan keyin shimmer **faqat birinchi marta** chiqsin (cold install). Boshqa hollarda mavjud snapshot darhol ko'rinadi.

### 4.4 Splash screen optimizatsiya
`flutter_native_splash` allaqachon yozilgan. Lekin:
```dart
// main.dart
runApp(...);
// run AFTER initial frame (don't block splash)
WidgetsBinding.instance.addPostFrameCallback((_) {
  // Background prefetch
  ref.read(apiClientProvider).listSpecies(redBook: true).ignore();
  ref.read(apiClientProvider).shopCategories().ignore();
});
```

### 4.5 `flutter_riverpod` `keepAlive` providerlar
Hozir har sahifa mount/dismount'da provider qayta yaratiladi → cache tushib qoladi. Asosiy data providerlarga `keepAlive: true`:

```dart
final speciesListProvider = FutureProvider.family<Paginated<Species>, String?>(
  (ref, category) async {
    ref.keepAlive();  // Provider o'lmasin
    return ref.watch(apiClientProvider).listSpecies(category: category);
  },
);
```

### 4.6 Build flag `--obfuscate --split-debug-info`
APK kichikroq → install tezroq:
```bash
flutter build apk --release --split-per-abi \
  --obfuscate \
  --split-debug-info=build/symbols \
  --tree-shake-icons \
  --dart-define=API_BASE=https://api.bioscan.uz/api
```

---

## 5. ✅ Order of operations — qaysidan boshlash

**Kun 1 (eng katta yutuqlar — 5 soat ishi):**
1. ✅ Postgres o'rnatish + migrate (1 soat)
2. ✅ Redis o'rnatish + cache_url qo'yish (15 daqiqa)
3. ✅ `bioscan.uz` domen sotib olish + Cloudflare proxy (1 soat)
4. ✅ Nginx server_name yangilash + Let's Encrypt sertifikat (30 daqiqa)
5. ✅ Flutter `defaultApiBase` ni `api.bioscan.uz` ga o'zgartirish (5 daqiqa)
6. ✅ Yangi APK build + test (1 soat)

**Kun 1 oxirida kutilgan natija:**
- Anonim catalog: 500ms → 50ms (Cloudflare cache hit)
- Authenticated: 500ms → 150ms (Postgres + Redis)
- Cold start: 1.7s → 400ms (HTTP/3 + 0-RTT)

**Kun 2-3 (Drift offline-first — 6 soat):**
1. Drift schema + repo qatlami
2. Seed JSON build script
3. UI provider'larini repo dan o'qishga ko'chirish
4. APK ichida birinchi shimmer faqat tarmoq yo'q paytda

**Kun 4 (image + scan tezlik — 2 soat):**
1. Scanner page'da `imageQuality=75, maxWidth=1280`
2. Server-side thumbnail (django-imagekit)

**Kun 5 (fine tuning — 2 soat):**
1. Database indekslar
2. Brotli nginx
3. Sentry sample 0.02
4. APK build flags + size audit

---

## 6. 🧪 Validation — har bosqichdan keyin

```bash
# 1. TTFB
curl -s -o /dev/null -w "TTFB:%{time_starttransfer}s\n" \
  'https://api.bioscan.uz/api/species/'
# Maqsad: <150ms warm, <300ms cold

# 2. Cache hit (Cloudflare)
curl -sI 'https://api.bioscan.uz/api/species/' | grep -i cf-cache
# Kutilgan: cf-cache-status: HIT

# 3. HTTP/3
curl --http3 -sI 'https://api.bioscan.uz/api/species/' 2>&1 | grep -i http
# Kutilgan: HTTP/3 200

# 4. APK size
ls -lh build/app/outputs/flutter-apk/app-arm64-v8a-release.apk
# Maqsad: <30 MB (hozir tekshirilsin)

# 5. Cold start (real device)
adb shell am force-stop com.bioscan.app
time adb shell am start -W -n com.bioscan.app/.MainActivity
# Maqsad: TotalTime <1500ms
```

---

## 7. 💸 Xarajatlar (haqiqiy)

| Resurs | Narx | Eslatma |
|---|---|---|
| Domain `bioscan.uz` | $10-30/yil | Reg.uz / Namecheap |
| Cloudflare Free | $0 | 100 GB/oy bandwidth bepul |
| VPS (mavjud Contabo) | $7/oy | Saqlanadi |
| PostgreSQL | $0 | Aynan VPS ichida |
| Redis | $0 | Aynan VPS ichida |
| **JAMI qo'shimcha** | **~$2/oy** ($30 domen / 12) | |

---

## 8. ⚠️ TUTUQLAR (xato qilmaslik kerak)

1. **SQLite'dan dump qilishdan oldin** `media/` papkasi tozalangani tekshirilsin — keraksiz fayllar ko'p bo'lishi mumkin.

2. **Cloudflare proxy yoqsangiz** Telegram webhook to'g'ridan-to'g'ri VPS'ga emas, `api.bioscan.uz/api/bot/webhook/`'ga sozlansin. Telegram IP'si Cloudflare WAF'dan o'tishi tekshirilsin (default Free plan'da o'tadi).

3. **CORS_ALLOW_ALL=True** production'da xavfli emas, chunki JWT bilan ishlaydi. Lekin shaxsiy ma'lumotni qaytaruvchi endpointlarda yana bir tekshirish foydali.

4. **Drift migration** SharedPreferences'dagi `togai:apicache:*` keyladan eski cache'larni invalidate qiling — schema o'zgargan bo'lsa nul JSON parse error chiqaradi.

5. **`dart-define=API_BASE`** har APK build da yangilanmasa eski URL qoladi — CI/CD'da `--dart-define` env'dan olinsin.

6. **Sentry SENTRY_TRACES** kamaytirsangiz, kritik xatolarni ham kamroq olasiz. Faqat barqaror production'da kamaytiring.

---

## 9. 📊 Final tezlik kutilmasi

| Ssenariy | Hozir | Kun 1 | Kun 5 |
|---|---|---|---|
| Cold install → Home | 6-8 s | 3 s | **<1.5 s** |
| Catalog ochish (cached) | 2-3 s | 200 ms | **<100 ms** |
| Catalog ochish (cold) | 3-4 s | 800 ms | **300 ms** |
| Shop sahifa | 4-5 s | 1 s | **400 ms** |
| Skanga jo'natish | 9-12 s | 8 s | **5-7 s** |
| Search query | 1-2 s | 400 ms | **150 ms** |
| Profile → Plan ko'rish | 1.5 s | 300 ms | **80 ms** (Drift) |

---

**Sana:** 2026-05-09
**Versiya:** 2.0 (real diagnostika asosida)
**Oldingi TZ:** `BACKEND_TZ_FOR_FLUTTER_SPEED.md` — VPS sozlash bo'yicha (saqlash kerak, lekin bu hujjat ustun)
