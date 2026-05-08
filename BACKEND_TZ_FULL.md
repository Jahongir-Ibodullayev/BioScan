# BioScan Backend TZ — 5 ta yangi feature

Maqsad: Flutter ilovasiga 5 ta yangi xizmatni ulash uchun backend tomonida bajariladigan ishlar. Har bir feature alohida bo'limda — model, endpoint, migration, dependency va environment variables.

**Stack**: Django 5.1.4 + DRF + PostgreSQL + Redis + Celery + Gunicorn (gthread).

**Flutter app `defaultApiBase`**: `https://bioscan.duckdns.org/api`

**Server**: `/root/apps/togai-backend/`, systemd service `togai-backend.service`, deploy `git pull && systemctl restart togai-backend`.

---

## 1. GPS Ekin maslahati (Crop Advisor)

### Maqsad
Foydalanuvchi telefonida GPS, ekin turi va sug'orish usulini tanlaydi → 30 kunlik ob-havo va tarixiy ma'lumotlar asosida **qachon ekish, qanday tayyorlash, qaysi nav, sug'orish jadvali** maslahat beriladi.

### Yondashuv
- Kichik mantiq **APK ichida** (rules-based, 0 ms): tuproq harorati, sovuq sanasi, ekish davri.
- AI tushuntirish va batafsil maslahat **backend'da** (kerak bo'lganda).
- Crop knowledge base **APK assets'ida** versiyalanadi, lekin backend yangilash uchun source-of-truth saqlaydi.

### Modellar (`crops/models.py` — yangi app)

```python
class Crop(models.Model):
    """Bitta ekin/o'simlik haqida ma'lumot bazasi."""
    slug = models.SlugField(max_length=80, unique=True)             # "kartoshka"
    name_uz = models.CharField(max_length=80)                       # "Kartoshka"
    name_ru = models.CharField(max_length=80, blank=True)
    name_lat = models.CharField(max_length=120, blank=True)         # "Solanum tuberosum"
    category = models.CharField(max_length=20)                      # sabzavot, meva, don, gul, dorivor
    icon_emoji = models.CharField(max_length=4, default="🥔")

    # Ekish parametrlari
    min_soil_temp_c = models.IntegerField(default=0, help_text="Ekish uchun min tuproq harorati")
    optimal_soil_temp_c = models.IntegerField(default=0)
    frost_sensitive = models.BooleanField(default=False)
    plant_window_start_month = models.IntegerField(default=3, help_text="Ekish davri boshi (1-12)")
    plant_window_end_month = models.IntegerField(default=5)
    days_to_harvest_min = models.IntegerField(default=80)
    days_to_harvest_max = models.IntegerField(default=120)

    # Sug'orish
    water_freq_days = models.IntegerField(default=5, help_text="Har necha kunda sug'orish")
    drought_tolerant = models.BooleanField(default=False)
    flood_tolerant = models.BooleanField(default=False)

    # Tuproq va sharoit
    soil_type = models.CharField(max_length=80, default="qum-tuproq")
    ph_min = models.DecimalField(max_digits=3, decimal_places=1, default=6.0)
    ph_max = models.DecimalField(max_digits=3, decimal_places=1, default=7.0)
    sun_hours_min = models.IntegerField(default=6)

    # Ko'rsatmalar
    soil_prep_uz = models.TextField(blank=True)
    planting_method_uz = models.TextField(blank=True)
    care_tips_uz = models.TextField(blank=True)
    common_pests = models.TextField(blank=True)

    # Naviar
    common_varieties = models.JSONField(default=list)
    # Misol: [{"name": "Nevskiy", "season": "early", "yield": "high", "notes": "..."}]

    image_url = models.URLField(blank=True, max_length=600)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name_uz",)
        indexes = [models.Index(fields=["category"])]


class Region(models.Model):
    """O'zbekiston viloyatlari + tarixiy iqlim ma'lumotlari."""
    slug = models.SlugField(max_length=40, unique=True)             # "tashkent"
    name_uz = models.CharField(max_length=40)
    name_ru = models.CharField(max_length=40, blank=True)
    # Bbox (lat min, lon min, lat max, lon max) — GPS → region uchun
    lat_min = models.DecimalField(max_digits=8, decimal_places=4)
    lat_max = models.DecimalField(max_digits=8, decimal_places=4)
    lon_min = models.DecimalField(max_digits=8, decimal_places=4)
    lon_max = models.DecimalField(max_digits=8, decimal_places=4)
    # Climate norms
    avg_last_frost_doy = models.IntegerField(help_text="Day of year — bahorgi oxirgi sovuq")
    avg_first_frost_doy = models.IntegerField(help_text="Kuzgi birinchi sovuq")
    annual_rainfall_mm = models.IntegerField(default=300)


class CropPlan(models.Model):
    """Foydalanuvchining ekish rejasi — keyinchalik eslatma yuborish uchun."""
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="crop_plans")
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE)
    lat = models.DecimalField(max_digits=8, decimal_places=4)
    lon = models.DecimalField(max_digits=8, decimal_places=4)
    irrigation = models.CharField(
        max_length=20,
        choices=[("drip", "Tomchi"), ("sprinkler", "Yomg'irlash"),
                 ("manual", "Qo'l"), ("none", "Yo'q")],
    )
    plot_size_m2 = models.IntegerField(null=True, blank=True)
    planned_plant_date = models.DateField()
    expected_harvest_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    notify = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["user", "-created_at"])]
```

### Endpointlar (`crops/urls.py`)

| Method | Path | Tavsif | Auth |
|---|---|---|---|
| GET | `/api/crops/` | Hamma ekinlar ro'yxati (Flutter assets sync uchun) | open |
| GET | `/api/crops/<slug>/` | Bitta ekin tafsilotlari | open |
| GET | `/api/crops/regions/` | Viloyatlar ro'yxati + iqlim normalari | open |
| POST | `/api/crops/advice/` | AI bilan kengaytirilgan maslahat (ixtiyoriy) | open (rate-limited) |
| GET | `/api/crops/plans/` | Foydalanuvchining ekish rejalari | required |
| POST | `/api/crops/plans/` | Yangi reja qo'shish | required |
| PATCH | `/api/crops/plans/<id>/` | Rejani yangilash / tugatish | required |
| DELETE | `/api/crops/plans/<id>/` | Rejani o'chirish | required |

### `/api/crops/advice/` — request/response

```http
POST /api/crops/advice/
Content-Type: application/json

{
  "crop_slug": "kartoshka",
  "lat": 41.31,
  "lon": 69.24,
  "irrigation": "drip",
  "plot_size_m2": 100,
  "soil_type": "qum-tuproq",
  "experience": "beginner"   // beginner | intermediate | expert
}

→ 200 OK
{
  "crop": "Kartoshka",
  "region": "Toshkent viloyati",
  "summary_uz": "Sizning hududda kartoshka ekish uchun eng yaxshi vaqt — mart oxiri / aprel boshi...",
  "best_plant_dates": ["2026-03-25", "2026-04-10"],
  "expected_harvest": "2026-07-15",
  "watering_schedule": [
    {"week": 1, "frequency_days": 7, "liters_per_m2": 4},
    {"week": 4, "frequency_days": 5, "liters_per_m2": 5},
    {"week": 8, "frequency_days": 5, "liters_per_m2": 6}
  ],
  "tips_uz": ["Ekishdan oldin tuproqni 25 sm chuqurlikda yumshating...", "..."],
  "warnings_uz": ["Aprelda sovuq tushishi mumkin — agroplenka tayyorlab qo'ying"],
  "recommended_variety": "Nevskiy",
  "ai_explanation": "Sovuq sanalari va sizning sug'orish tizmingizga qarab..."
}
```

**Ichki ish**:
1. `lat/lon` → `Region` lookup (bbox bo'yicha)
2. Open-Meteo'dan 30 kunlik prognoz (forecast) + 5 yillik tarixiy (climate-archive)
3. `Crop.min_soil_temp_c` va prognoz tuproq haroratiga qarab eng yaqin to'g'ri sanani topish
4. AI prompt → OpenRouter (gpt-4o-mini, 500 token) → `ai_explanation`
5. **Cache**: `(crop_slug, region_slug, irrigation, week_of_year)` 24 soat Redis'da

### Open-Meteo integratsiyasi (`crops/services/weather.py`)

```python
import httpx

OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"

async def get_30day_forecast(lat, lon):
    params = {
        "latitude": lat, "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,soil_temperature_0_to_7cm_max,"
                 "soil_temperature_0_to_7cm_min,precipitation_sum",
        "timezone": "Asia/Tashkent",
        "forecast_days": 16,    # max free
        "past_days": 14,
    }
    async with httpx.AsyncClient() as c:
        r = await c.get(OPEN_METEO_FORECAST, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
```

### Bezovor xizmatlari va dependencies

Yangi requirements.txt qatorlari:
```
httpx==0.27.2          # Open-Meteo async client
celery==5.4.0          # Eslatmalarni rejalashtirish (allaqachon bo'lsa tekshiring)
django-celery-beat==2.7.0
```

### Migrations
```bash
python manage.py makemigrations crops
python manage.py migrate
python manage.py loaddata crops/fixtures/seed_crops.json    # 20 ekin tayyor JSON
python manage.py loaddata crops/fixtures/seed_regions.json  # 14 viloyat
```

### Seed data

`crops/fixtures/seed_crops.json` da kamida **20 ekin**:
kartoshka, pomidor, bodring, sabzi, piyoz, sarimsoq, qovun, tarvuz, kungaboqar, makka, bug'doy, sholi, paxta, no'xat, mosh, loviya, qulupnay, olma, gilos, anor.

Har bir ekin uchun yuqoridagi modelning hamma maydonlarini to'ldirish kerak. Mahalliy agronom yoki Wikipedia + AI yordamida yarating.

`crops/fixtures/seed_regions.json` da **14 viloyat** + Toshkent shahar = 13 ta:
Toshkent, Andijon, Buxoro, Farg'ona, Jizzax, Namangan, Navoiy, Qashqadaryo, Qoraqalpog'iston, Samarqand, Sirdaryo, Surxondaryo, Xorazm.

### Eslatmalar (Celery beat)

`/api/crops/plans/` orqali kiritilgan reja uchun avtomatik eslatmalar:
- 3 kun oldin: "Kartoshka ekishingizga 3 kun qoldi"
- Ekish kuni: "Bugun kartoshka ekish vaqti"
- Sug'orish jadvaliga qarab har 5-7 kun: "Bugun sug'oring"

Celery task: `crops/tasks.py:send_planting_reminder` — har kun ertalab 7:00 da ishga tushadi.

---

## 2. Offline Xarita

### Maqsad
Foydalanuvchi internet yo'q joyda ham xarita ko'rishi (skanlangan turlar markerlari bilan).

### Yondashuv
- **Frontend tomonida `flutter_map_tile_caching`** paketi (raster tile keshi)
- **Backend role**:
  - Foydalanuvchi marker'larini kichik chunk-lar bilan beradi (lat/lon bbox, kategoriya)
  - Region MBTiles fayllarini optsion ravishda CDN'dan beradi (15-20 MB har viloyat)

### Endpoint qo'shish (`mapdata/views.py` ga)

| Method | Path | Tavsif |
|---|---|---|
| GET | `/api/map/markers/?bbox=lat1,lon1,lat2,lon2&cat=plant` | Bbox ichidagi markerlar (max 500) |
| GET | `/api/map/regions/<slug>/mbtiles_url/` | MBTiles offline pack URL'i |

### MBTiles tayyorlash (alohida ish)
```bash
# Toshkent viloyati uchun:
mb-util --image_format=png input_tiles/ tashkent.mbtiles
# Yoki tilemaker bilan OSM dan:
tilemaker --input osm/uzbekistan.pbf --output tiles/uz.mbtiles --bbox 60,38,73,45
```

MBTiles fayllar S3 yoki Cloudflare R2'da saqlanadi, backend faqat URL beradi (raqamga qarab).

### Database mavjud
`mapdata.Marker` allaqachon bor — `lat, lon, species, category, photo_url, created_at`. Faqat `bbox` filtri qo'shing.

```python
# views.py
class MarkersView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        bbox = request.GET.get("bbox", "")
        try:
            lat1, lon1, lat2, lon2 = [float(x) for x in bbox.split(",")]
        except ValueError:
            return Response({"results": []})
        cat = request.GET.get("cat")
        qs = Marker.objects.filter(
            lat__gte=min(lat1, lat2), lat__lte=max(lat1, lat2),
            lon__gte=min(lon1, lon2), lon__lte=max(lon1, lon2),
        )
        if cat:
            qs = qs.filter(category=cat)
        qs = qs[:500]
        return Response({"results": MarkerSerializer(qs, many=True).data})
```

Index qo'shish:
```python
class Marker(models.Model):
    ...
    class Meta:
        indexes = [
            models.Index(fields=["lat", "lon"]),
            models.Index(fields=["category"]),
        ]
```

---

## 3. TFLite Offline Skaner

### Maqsad
Internet yo'q bo'lganda ham telefon ichida AI bilan o'simlik/hayvon turini aniqlash.

### Yondashuv
- 50-100 MB TFLite model — APK ichida emas, **ilk ishga tushirishda yuklab olinadi**
- Model: PlantNet/iNaturalist embedding modeli yoki MobileNetV3 + custom head
- **Backend role**: model fayllarini saqlash + version tracking, fallback OpenRouter chaqiriqlari

### Modellar (`scanner/models.py` ga qo'shish)
```python
class TFLiteModel(models.Model):
    """TFLite model versiyalari."""
    name = models.CharField(max_length=40, unique=True)        # "plants_v1"
    version = models.CharField(max_length=20)                  # "1.0.0"
    file = models.FileField(upload_to="tflite/")
    size_bytes = models.BigIntegerField()
    sha256 = models.CharField(max_length=64)
    classes_url = models.URLField(blank=True)                  # JSON: id → species_slug
    accuracy = models.FloatField(default=0.85)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
```

### Endpointlar
| Method | Path | Tavsif |
|---|---|---|
| GET | `/api/scanner/models/active/` | Joriy faol model: `{name, version, url, sha256, size, classes_url}` |
| POST | `/api/scanner/scan/` | Mavjud (cloud AI) — fallback uchun ishlatiladi agar TFLite confidence < 0.6 |
| POST | `/api/scanner/scan/feedback/` | Foydalanuvchi to'g'ri/noto'g'ri belgilashi (model trening uchun) |

### Dataset va training (alohida ish)

Bu kod backend repository'sida emas — alohida `bioscan-ml/` repo'da:
1. PlantNet API yoki iNaturalist'dan O'zbekistonga oid 100+ tur uchun rasm yig'ish (~5000 rasm)
2. MobileNetV3-Small + transfer learning
3. TFLite quantize (int8) → 50 MB
4. `tf-keras` da `model.save_weights()` → `.tflite` convert
5. Backend admin'dan upload

Birinchi versiyada **avval mashhur turlar** (kartoshka, pomidor, olma, anor, gilos, sigir, qo'y, tovuq, bug'doy, sholi — 10-20 ta) — keyin kengaytirish.

### Flutter ulanishi (eslatma — keyin men qilaman)
- `tflite_flutter: ^0.10.4` paketi
- Birinchi ishga tushirishda model yuklab olish, sha256 tekshirish, app cache'ga qo'yish
- Skanerlash: rasm → 224×224 resize → model → top-3 sinflar → confidence < 0.6 bo'lsa `/api/scanner/scan/` ga fallback

---

## 4. Push Xabarnomalar (FCM)

### Holat
`accounts/push.py` da `register_fcm_token` mavjud. Faqat sending logic kerak.

### Modellar (`accounts/models.py` ga qo'shish — agar yo'q bo'lsa)
```python
class FCMToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="fcm_tokens")
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=10, choices=[("android", "Android"), ("ios", "iOS")])
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
```

### Yangi endpointlar (`accounts/urls.py` ga qo'shish)
| Method | Path | Tavsif |
|---|---|---|
| POST | `/api/auth/fcm/register/` | (mavjud) FCM token saqlash |
| POST | `/api/auth/fcm/unregister/` | (mavjud) Tokenni o'chirish |
| POST | `/api/admin/notifications/broadcast/` | **Yangi** — barcha foydalanuvchilarga xabar (admin only) |

### FCM yuborish servisi (`togai/services/fcm.py` — yangi)
```python
import firebase_admin
from firebase_admin import credentials, messaging

cred = credentials.Certificate(settings.FCM_CREDENTIALS_PATH)
firebase_admin.initialize_app(cred)


def send_to_user(user, title, body, data=None):
    tokens = list(user.fcm_tokens.filter(is_active=True).values_list("token", flat=True))
    if not tokens:
        return 0
    msg = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data=data or {},
        tokens=tokens,
    )
    response = messaging.send_each_for_multicast(msg)
    # Mark dead tokens inactive
    for idx, resp in enumerate(response.responses):
        if not resp.success and "registration-token-not-registered" in str(resp.exception):
            FCMToken.objects.filter(token=tokens[idx]).update(is_active=False)
    return response.success_count


def broadcast(title, body, data=None, segment=None):
    qs = FCMToken.objects.filter(is_active=True)
    if segment == "active_7d":
        qs = qs.filter(user__last_login__gte=timezone.now() - timedelta(days=7))
    tokens = list(qs.values_list("token", flat=True))
    # batch by 500 (FCM limit)
    sent = 0
    for i in range(0, len(tokens), 500):
        batch = tokens[i:i+500]
        msg = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
            tokens=batch,
        )
        sent += messaging.send_each_for_multicast(msg).success_count
    return sent
```

### Avtomatik xabarlar (Celery beat, `togai/celery.py`)
```python
beat_schedule = {
    # Har kun ertalab 7:00 — bugungi ekish/sug'orish eslatmalari
    "crop-plan-reminders": {
        "task": "crops.tasks.send_daily_reminders",
        "schedule": crontab(hour=7, minute=0),
    },
    # Har juma 18:00 — haftalik tabiat ma'lumotlari
    "weekly-nature-tip": {
        "task": "togai.tasks.send_weekly_tip",
        "schedule": crontab(hour=18, minute=0, day_of_week=5),
    },
}
```

### Dependencies
```
firebase-admin==6.5.0
```

### Environment variables
```bash
FCM_CREDENTIALS_PATH=/root/apps/togai-backend/secrets/firebase-adminsdk.json
```

Firebase console'dan service account JSON yuklab olib serverga qo'yish.

---

## 5. Server'ni yaqinlashtirish (ops, kod yo'q)

### Variant A — Yandex Cloud (Moskva) yoki Selectel
- VPS: 2 vCPU, 4 GB RAM, 40 GB SSD
- Narxi: ~$8-12/oy
- Ping UZ'dan: ~50-80 ms
- Migratsiya: `pg_dump` + `rsync` + DNS
- Vaqt: 1-2 soat

### Variant B — Cloudflare Tunnel + R2
- Hozirgi VPS qoladi
- Cloudflare oldida → TLS Toshkent edge'da
- Yo'l: `cloudflared service install --token <token>`
- Bepul, 5 daqiqa setup
- Ping UZ'dan TLS uchun: ~30 ms (lekin origin Germaniya'da qoladi)

**Tavsiya**: avval Variant B (bepul, 30 ms), keyin trafik o'sishi bilan Variant A.

---

## Umumiy o'zgarishlar

### Yangi Django apps
`INSTALLED_APPS` ga qo'shish:
```python
"crops",
```

(scanner, mapdata, accounts mavjud)

### URL routing (`togai/urls.py`)
```python
urlpatterns = [
    ...
    path("api/crops/", include("crops.urls")),
    ...
]
```

### `requirements.txt` ga qo'shilishi kerak
```
httpx==0.27.2
firebase-admin==6.5.0
django-celery-beat==2.7.0
```

### `.env` ga qo'shilishi kerak
```
OPEN_METEO_BASE=https://api.open-meteo.com/v1
FCM_CREDENTIALS_PATH=/root/apps/togai-backend/secrets/firebase-adminsdk.json
```

### Migratsiya tartibi
```bash
git pull
./venv/bin/pip install -r requirements.txt
./venv/bin/python manage.py makemigrations crops
./venv/bin/python manage.py migrate
./venv/bin/python manage.py loaddata crops/fixtures/seed_crops.json
./venv/bin/python manage.py loaddata crops/fixtures/seed_regions.json
systemctl restart togai-backend.service
systemctl restart togai-celery.service     # agar Celery ishlatsangiz
```

---

## Nima keyin

Backend tugagach, men Flutter tomondan quyidagilarni ulayman:
1. **Crop Advisor sahifasi** — GPS + ekin tanlash + maslahat ko'rsatish
2. **Crop knowledge base sync** — `/api/crops/` dan JSON faylga yozib olish (1-marta yoki versiya o'zgarganda)
3. **Offline xarita** — `flutter_map_tile_caching` + bbox query'lar
4. **TFLite skanner** — `tflite_flutter` + cloud fallback
5. **Push** — Firebase setup + `/api/auth/fcm/register/` chaqirish

Har bir feature uchun Flutter tomondagi ish 1-3 kun.
