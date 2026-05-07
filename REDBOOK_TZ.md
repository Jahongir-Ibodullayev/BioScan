# 📕 BioScan — Qizil Kitob (Red Book) Backend TZ

**Maqsad:** O'zbekiston Qizil Kitobidagi himoyadagi turlarni backend bazasiga to'liq kiritish va Flutter ilovasida ko'rsatish.

---

## 1. 📊 KO'LAM (Scope)

O'zbekiston Qizil Kitobining 4-nashri (2019) bo'yicha:
- **324 ta o'simlik turi** (gulli, qoziqorin, suvo'tlar)
- **184 ta hayvon turi** (sutemizuvchi, qush, baliq, sudralib yuruvchi, hasharot)

**Minimum talab — 100 ta turi (eng mashhurlari).**
**Optimal talab — 500+ tur (to'liq Qizil Kitob).**

---

## 2. 🗄️ DATA MODEL — `catalog.Species`

Mavjud model (DB'da saqlash kerak):

```python
class Species:
    slug: str             # "tulipa-greigii"
    name: str             # "Greig lolasi" (O'zbekcha)
    latin: str            # "Tulipa greigii"
    category: str         # giyoh|daraxt|gul|jonivor|qush|hasharot|qoziqorin|ilon|baliq
    iucn_status: str      # LC|NT|VU|EN|CR|EW|EX|DD|NE
    red_book: bool        # MAJBURIY = True
    
    # Tavsif
    summary: str          # 1-2 jumla qisqa
    description: str      # 4-6 jumla to'liq tavsif
    habitat: str          # Yashash joyi (2-3 jumla)
    uses: str             # Foydasi (3-4 jumla)
    warnings: str         # Xavfi (2-3 jumla)
    first_aid: str        # Birinchi yordam (agar zaharli)
    regions: str          # Tarqalgan hududlar (Toshkent, Surxondaryo va h.k.)
    
    # Rasm
    image: ImageField     # Yuklangan rasm (yoki)
    image_url: URLField   # Tashqi URL (Wikimedia, iNat)
    
    # Huquqiy
    fine_bhm_min: int     # Jarima minimum (BHM = Bazaviy hisoblash miqdori)
    fine_bhm_max: int     # Jarima maksimum
    law_article: str      # Qonun moddasi (masalan "JK 200-modda")
    external_ref: str     # Manba URL (UN-CITES, IUCN va h.k.)
```

---

## 3. 📋 KATEGORIYA TAQSIMI

Minimum 100 turdan tarkibi:

| Kategoriya | Slug | Soni | Misollar |
|---|---|---|---|
| 🌷 Gullar | `gul` | 25 | Greig lolasi, Buxoro fritillariyasi, Tyan-Shan irisi |
| 🌳 Daraxtlar | `daraxt` | 15 | Tarvuz daraxti, Farg'ona archasi, Pista yong'og'i |
| 🌿 Giyohlar | `giyoh` | 20 | Manjirik, Sho'r yantoq, Tog' yalpizi |
| 🦊 Sutemizuvchilar | `jonivor` | 15 | Qor barsi, Tyan-Shan ayig'i, Ko'rcha, Gepard |
| 🦅 Qushlar | `qush` | 15 | Olmaxon, Pallas burguti, Tunichi, Burgut |
| 🐍 Sudralib yuruvchi | `ilon` | 5 | Gyurza, Markaziy Osiyo toshbaqasi, Echkemar |
| 🐟 Baliqlar | `baliq` | 5 | Sirdaryo qotirma, Aral ko'l qarmog'i |

---

## 4. 🔢 IUCN STATUS QO'LLANISHI

| Kod | Ma'no | Misollar | Jarima (BHM) |
|---|---|---|---|
| **EX** | Yo'q bo'lib ketgan | (yo'q) | — |
| **EW** | Tabiatda yo'q (faqat zoopark) | Pers leopardi (?) | — |
| **CR** | Tanqidiy xavfda | Saypul, Buxoro qo'yi | 5000-15000 |
| **EN** | Xavfda | Greig lolasi, Pallas burguti | 1000-5000 |
| **VU** | Zaif | Qor barsi, Tyan-Shan ayig'i | 500-2000 |
| **NT** | Xavfga yaqin | Eremurus, Asio Otus | 50-300 |

---

## 5. 🌐 RASM URL — qaysi manbadan

Har turi uchun rasm. Ustunlik:
1. **Wikimedia Commons** — bepul, sifatli, to'g'ri litsenziya
2. **iNaturalist** — ko'p hayvon kuzatuvi (`https://static.inaturalist.org/photos/...`)
3. **Plantarium.ru** — o'simliklar (rus tilida lekin rasmlar yaxshi)
4. **UzFlora.uz** — milliy manba (agar mavjud bo'lsa)

⚠️ **MAJBURIY:** image_url'da to'g'ri rasm bo'lishi shart — bo'sh bo'lsa Flutter placeholder ko'rsatadi.

**Tavsiya format:**
```
https://upload.wikimedia.org/wikipedia/commons/thumb/X/XX/Filename.jpg/800px-Filename.jpg
```

---

## 6. ⚙️ BACKEND SOZLASH

### 6.1 Migration tekshirish
```bash
cd /var/www/togai-backend
source venv/bin/activate
python manage.py showmigrations catalog
# barcha migration'lar applied bo'lishi kerak
```

### 6.2 Seed buyruq tayyor
```bash
python manage.py seed_redbook
```
Bu buyruq `catalog/management/commands/seed_redbook.py` faylda. Hozir 103 ta turini qo'shadi. Bazani **kengaytirish** uchun shu faylga yangi turlarni qo'shing.

### 6.3 Import CSV/JSON orqali (kengroq baza uchun)
**Tavsiya — JSON fayl tayyorlash:**
```json
[
  {
    "slug": "tulipa-greigii",
    "name": "Greig lolasi",
    "latin": "Tulipa greigii",
    "category": "gul",
    "iucn_status": "EN",
    "red_book": true,
    "summary": "...",
    "description": "...",
    "habitat": "...",
    "uses": "...",
    "warnings": "...",
    "regions": "Toshkent, Surxondaryo",
    "image_url": "https://upload.wikimedia.org/.../Tulipa_greigii.jpg",
    "fine_bhm_min": 30,
    "fine_bhm_max": 100,
    "law_article": "JK 200-modda"
  },
  ...
]
```

**Import buyruq (yangi yozish kerak):**
```python
# catalog/management/commands/import_redbook_json.py
from catalog.models import Species
import json

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("file")
    
    def handle(self, *args, **opts):
        with open(opts["file"]) as f:
            data = json.load(f)
        for item in data:
            slug = item.pop("slug")
            Species.objects.update_or_create(slug=slug, defaults=item)
        self.stdout.write(f"✓ {len(data)} ta tur import qilindi")
```

Ishlatish:
```bash
python manage.py import_redbook_json redbook_500.json
```

---

## 7. 📡 API ENDPOINT — Flutter chaqiradi

### 7.1 Qizil kitob ro'yxati
```
GET /api/species/?red_book=true&page=1
```
**Javob:**
```json
{
  "count": 100,
  "next": "https://api.bioscan.uz/api/species/?red_book=true&page=2",
  "results": [
    {
      "id": 1,
      "slug": "tulipa-greigii",
      "name": "Greig lolasi",
      "latin": "Tulipa greigii",
      "category": "gul",
      "iucn_status": "EN",
      "red_book": true,
      "summary": "...",
      "picture": "https://images.weserv.nl/?url=...&w=400"
    },
    ...
  ]
}
```

### 7.2 Detail
```
GET /api/species/tulipa-greigii/
```
Barcha maydonlar bilan to'liq response.

### 7.3 Filter (kategoriya bo'yicha)
```
GET /api/species/?red_book=true&category=gul
GET /api/species/?red_book=true&iucn=CR
GET /api/species/?red_book=true&search=lola
```

---

## 8. ✅ TEKSHIRUV (Acceptance Criteria)

Backend tayyor deb hisoblash uchun:

```bash
# 1. Bazada minimum 100 ta Qizil kitob species bor
curl -s "https://api.bioscan.uz/api/species/?red_book=true" | jq .count
# kutilgan: >= 100

# 2. Har xil kategoriyalar bor
for cat in gul daraxt giyoh jonivor qush ilon; do
  echo "$cat:"
  curl -s "https://api.bioscan.uz/api/species/?red_book=true&category=$cat" | jq '.results | length'
done
# kutilgan: har biri >= 5

# 3. Detail sahifa to'liq ma'lumot
curl -s "https://api.bioscan.uz/api/species/tulipa-greigii/" | jq 'keys'
# kutilgan: name, latin, summary, description, habitat, uses, warnings, regions, picture

# 4. Rasmlar URL'lari ishlaydi
curl -sI "$(curl -s 'https://api.bioscan.uz/api/species/?red_book=true' | jq -r '.results[0].picture')" | head -1
# kutilgan: HTTP/2 200

# 5. Eng mashhur turlar mavjud
for slug in tulipa-greigii ovis-vignei-bochariensis vipera-lebetina; do
  echo -n "$slug: "
  curl -s -o /dev/null -w "%{http_code}\n" "https://api.bioscan.uz/api/species/$slug/"
done
# kutilgan: hammasi 200

# 6. CR/EN statuslar to'g'ri
curl -s "https://api.bioscan.uz/api/species/?red_book=true&iucn=CR" | jq .count
# kutilgan: >= 5
```

---

## 9. 📱 FLUTTER UI INTEGRATSIYASI

Flutter `RedBookPage` — quyidagilarni ko'rsatadi:
- Yuqorida ogohlantirish kartochkasi: "Muhofazadagi 100+ tur"
- Ro'yxatda har turi:
  - 🖼 Rasm (kichik)
  - 📛 O'zbekcha nom + lotincha (italik)
  - 🏷 IUCN status (rangli badge: CR=qizil, EN=qizil, VU=sariq)
  - 💰 Jarima (BHM da)
- Bossa → detail sahifa to'liq ma'lumot bilan

---

## 10. 🎯 PRIORITET TURLAR (eng birinchi 30)

Eng dolzarb — bular bilan boshlang:

**O'simliklar (15):**
1. Greig lolasi *(Tulipa greigii)*
2. Kaufman lolasi *(Tulipa kaufmanniana)*
3. Buxoro fritillariyasi *(Fritillaria bucharica)*
4. Tyan-Shan irisi *(Iris rosenbachiana)*
5. Yirik eremurus *(Eremurus robustus)*
6. Sevqir terak *(Populus pruinosa)*
7. Buxoro guli *(Tulipa lehmanniana)*
8. Manjirik *(Mandragora turcomanica)*
9. Tarvuz daraxti *(Crataegus pontica)*
10. Pomir yantoqi *(Alhagi tjanschanica)*
11. Tog' yalpizi *(Mentha asiatica)*
12. Sho'r yantoq *(Halimocnemis monandra)*
13. Pista yong'og'i *(Pistacia vera)*
14. Farg'ona archasi *(Juniperus turkestanica)*
15. Sirdaryo bodomi *(Amygdalus communis)*

**Hayvonlar (15):**
1. Qor barsi *(Panthera uncia)*
2. Tyan-Shan ayig'i *(Ursus arctos isabellinus)*
3. Buxoro qo'yi *(Ovis vignei bochariensis)*
4. Markaziy Osiyo silovsini *(Lynx lynx isabellina)*
5. Ko'rcha *(Capra sibirica)*
6. Gyurza *(Macrovipera lebetina)*
7. Cho'l toshbaqasi *(Agrionemys horsfieldii)*
8. Pallas burguti *(Haliaeetus leucoryphus)*
9. Olmaxon *(Strix nivicolum)*
10. Saypul *(Vormela peregusna)*
11. Sirdaryo qotirma *(Pseudoscaphirhynchus fedtschenkoi)*
12. Aral mursisi *(Luciobarbus brachycephalus)*
13. Apollon kapalagi *(Parnassius apollo)*
14. Markaziy Osiyo nayzaburuni *(Cyrtopodion turcmenicum)*
15. Kaspiy palanga *(Panthera pardus tulliana)*

---

## 11. 📞 ALOQA / ESKALATSIYA

Savol bo'lsa:
1. Texnik: Flutter API tomonida → mendan so'rang
2. Qizil kitob ma'lumotlari: O'zbekiston Fanlar akademiyasi, Botanika instituti
3. Manba: "O'zbekiston Respublikasi Qizil kitobi", 4-nashr, 2019, Toshkent

---

**Yozildi:** BioScan Frontend Team (Flutter)
**Qabul qiluvchi:** Backend developer
**Sana:** 2026-05-07
**Versiya:** 1.0
**Format:** Markdown — server'ga upload qiling yoki PR yarating

---

## 🚀 ESLATMA

Server'da `seed_redbook` buyrug'i ishlaydi (men yozib qo'yganman). Kengaytirish uchun shu fayl ichiga yangi turlarni qo'shing:

```
/var/www/togai-backend/catalog/management/commands/seed_redbook.py
```

Faylda `REDBOOK_SPECIES` ro'yxati bor — uni kengaytiring va qaytadan `python manage.py seed_redbook` ishga tushiring.
