"""`python manage.py seed_redbook` — 30+ real O'zbekiston Qizil kitob turlari (2019)."""
from django.core.management.base import BaseCommand

from catalog.models import Species

# O'zbekiston Qizil kitob (2019) + IUCN + filters
REDBOOK_DATA = [
    # ====== O'SIMLIKLAR (324 dan eng muhimlari) ======
    {"slug": "tulipa-greigii", "name": "Greig lolasi", "latin": "Tulipa greigii",
     "category": "gul", "icon_name": "flower", "red_book": True, "iucn_status": "VU",
     "summary": "Chimyon tog'larida gullaydi. Endemik.",
     "habitat": "Toshli yon bag'irlar, 600-1800m",
     "warnings": "Qizil kitobda. Uzish jarima.",
     "regions": "Toshkent, Samarqand, Jizzax",
     "fine_bhm_min": 50, "fine_bhm_max": 100, "law_article": "MK 204-modda",
     "halal_status": "unknown", "is_medicinal": False,
     "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Tulipa_greigii_1.jpg/800px-Tulipa_greigii_1.jpg"},

    {"slug": "tulipa-kaufmanniana", "name": "Kaufman lolasi", "latin": "Tulipa kaufmanniana",
     "category": "gul", "icon_name": "flower", "red_book": True, "iucn_status": "LC",
     "summary": "Oq-sariq ranglarda gullaydigan tog' lolasi.",
     "habitat": "Tog' yon bag'irlari, 1000-2500m",
     "regions": "Tyan-Shan, Pomir-Oloy",
     "fine_bhm_min": 50, "fine_bhm_max": 100, "law_article": "MK 204-modda",
     "halal_status": "unknown"},

    {"slug": "juniperus-seravschanica", "name": "Zarafshon archasi", "latin": "Juniperus seravschanica",
     "category": "daraxt", "icon_name": "tree", "red_book": True, "iucn_status": "EN",
     "summary": "500 yilgacha yashaydigan muqaddas daraxt.",
     "habitat": "Tog' cho'qqilari, 1500-3000m",
     "warnings": "Kesish — jinoiy javobgarlik.",
     "uses": "Efir moyi, havo poklash. Kesish TA'QIQLANADI.",
     "regions": "Zarafshon, G'arbiy Tyan-Shan",
     "fine_bhm_min": 100, "fine_bhm_max": 200, "law_article": "MK 204-modda + Jinoiy 202"},

    {"slug": "juniperus-turkestanica", "name": "Turkiston archasi", "latin": "Juniperus turkestanica",
     "category": "daraxt", "icon_name": "tree", "red_book": True, "iucn_status": "LC",
     "summary": "Baland tog'larning yashashga chidamli archasi.",
     "habitat": "2500-3500m", "regions": "Pomir-Oloy",
     "fine_bhm_min": 100, "fine_bhm_max": 200, "law_article": "MK 204-modda"},

    {"slug": "iris-magnifica", "name": "Ulug'vor iris", "latin": "Iris magnifica",
     "category": "gul", "icon_name": "flower", "red_book": True, "iucn_status": "VU",
     "summary": "Yirik zarg'aldoq-binafsha gul. Endemik.",
     "habitat": "Tog' yaylovlari, 1200-2000m",
     "regions": "Nurota, Qoratog'",
     "fine_bhm_min": 40, "fine_bhm_max": 80, "law_article": "MK 204-modda"},

    {"slug": "allium-suvorovii", "name": "Suvorov piyozi", "latin": "Allium suvorovii",
     "category": "gul", "icon_name": "flower", "red_book": True, "iucn_status": "NT",
     "summary": "Katta sharsimon gul. Ekstremal issiqlikka chidamli.",
     "habitat": "Cho'l yon bag'ri",
     "regions": "Qizilqum",
     "fine_bhm_min": 30, "fine_bhm_max": 60, "law_article": "MK 204-modda"},

    {"slug": "eremurus-regelii", "name": "Regel shariqi", "latin": "Eremurus regelii",
     "category": "gul", "icon_name": "flower", "red_book": True, "iucn_status": "VU",
     "summary": "Uzun bo'yli gul minorasi.",
     "habitat": "Tog' yaylovlari",
     "regions": "Farg'ona, Toshkent",
     "fine_bhm_min": 30, "fine_bhm_max": 70, "law_article": "MK 204-modda"},

    {"slug": "paeonia-intermedia", "name": "Oraliq piyon", "latin": "Paeonia intermedia",
     "category": "gul", "icon_name": "flower", "red_book": True, "iucn_status": "VU",
     "summary": "Gul va meditsina uchun qimmatli.",
     "habitat": "Tog' o'rmonlari",
     "is_medicinal": True,
     "regions": "Chotqol, Qurama",
     "fine_bhm_min": 50, "fine_bhm_max": 100, "law_article": "MK 204-modda"},

    {"slug": "peganum-harmala", "name": "Isiriq", "latin": "Peganum harmala",
     "category": "giyoh", "icon_name": "leaf", "red_book": False, "iucn_status": "LC",
     "summary": "Shifobaxsh, tutatish uchun ishlatiladi.",
     "habitat": "Qurg'oqchil yonbag'irlar",
     "uses": "Tutatish, xona poklash, ba'zi kasalliklar.",
     "warnings": "Ichishda ehtiyot. Dozasi muhim.",
     "is_medicinal": True, "halal_status": "halal",
     "regions": "Barcha UZ",
     "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/94/Peganum_harmala_003.JPG/800px-Peganum_harmala_003.JPG"},

    {"slug": "ferula-foetida", "name": "Sassiq andiz", "latin": "Ferula foetida",
     "category": "giyoh", "icon_name": "leaf", "red_book": True, "iucn_status": "NT",
     "summary": "Qimmatli dorivor giyoh. Sassiq hidli.",
     "habitat": "Cho'l-dasht", "is_medicinal": True,
     "regions": "Qashqadaryo, Surxondaryo",
     "fine_bhm_min": 20, "fine_bhm_max": 50, "law_article": "MK 204-modda"},

    {"slug": "artemisia-leucodes", "name": "Shuvoq", "latin": "Artemisia leucodes",
     "category": "giyoh", "icon_name": "leaf", "red_book": False, "iucn_status": "LC",
     "summary": "O'zbek tabobatining eng tarqalgan giyohi.",
     "uses": "Damlama, me'daga yaxshi, antiparazitar.",
     "is_medicinal": True, "halal_status": "halal",
     "regions": "Barcha UZ"},

    {"slug": "glycyrrhiza-glabra", "name": "Qizilmiya", "latin": "Glycyrrhiza glabra",
     "category": "giyoh", "icon_name": "leaf", "red_book": False, "iucn_status": "LC",
     "summary": "Shirin ildiz — yo'tal va tomoqqa.",
     "uses": "Ildizi damlab ichiladi.", "is_medicinal": True, "is_edible": True,
     "halal_status": "halal",
     "regions": "Qashqadaryo, Jizzax"},

    # ====== HAYVONLAR ======
    {"slug": "panthera-uncia", "name": "Qor bars", "latin": "Panthera uncia",
     "category": "jonivor", "icon_name": "paw", "red_book": True, "iucn_status": "VU",
     "summary": "O'zbekistonda 50-100 ta qolgan.",
     "habitat": "Baland tog'lar, 3000m+",
     "warnings": "Jinoiy javobgarlik: 500-1000 BHM",
     "regions": "Pomir-Oloy, Chotqol",
     "fine_bhm_min": 500, "fine_bhm_max": 1000, "law_article": "Jinoiy 202-modda"},

    {"slug": "uncia-uncia", "name": "Ilvirs", "latin": "Lynx lynx isabellinus",
     "category": "jonivor", "icon_name": "paw", "red_book": True, "iucn_status": "EN",
     "summary": "Tog' silovsini. Noyob turkman turi.",
     "habitat": "Tog' o'rmonlari",
     "regions": "Zarafshon, G'arbiy Tyan-Shan",
     "fine_bhm_min": 300, "fine_bhm_max": 600, "law_article": "Jinoiy 202-modda"},

    {"slug": "saiga-tatarica", "name": "Sayg'oq", "latin": "Saiga tatarica",
     "category": "jonivor", "icon_name": "paw", "red_book": True, "iucn_status": "CR",
     "summary": "Kritik xavfda. Brakonerlik tufayli.",
     "habitat": "Ustyurt cho'li",
     "warnings": "Kritik holatda. Ov — jinoiy jihat.",
     "regions": "Qoraqalpog'iston, Ustyurt",
     "fine_bhm_min": 800, "fine_bhm_max": 1500, "law_article": "Jinoiy 202-modda"},

    {"slug": "gazella-subgutturosa", "name": "Jayran", "latin": "Gazella subgutturosa",
     "category": "jonivor", "icon_name": "paw", "red_book": True, "iucn_status": "VU",
     "summary": "O'rta Osiyo cho'l gazellesi.",
     "habitat": "Qizilqum, Ustyurt",
     "regions": "Markaziy-g'arbiy UZ",
     "fine_bhm_min": 400, "fine_bhm_max": 800, "law_article": "Jinoiy 202-modda"},

    {"slug": "ursus-arctos-isabellinus", "name": "Tyan-Shan ayig'i", "latin": "Ursus arctos isabellinus",
     "category": "jonivor", "icon_name": "paw", "red_book": True, "iucn_status": "LC",
     "summary": "Kichik subturi. O'zbekistonda noyob.",
     "habitat": "Baland tog' o'rmonlari",
     "regions": "Chotqol, G'arbiy Tyan-Shan",
     "fine_bhm_min": 600, "fine_bhm_max": 1200, "law_article": "Jinoiy 202-modda"},

    {"slug": "marmota-menzbieri", "name": "Menzbir suvarakmurti", "latin": "Marmota menzbieri",
     "category": "jonivor", "icon_name": "paw", "red_book": True, "iucn_status": "EN",
     "summary": "Tyan-Shan subalp yaylovlari endemigi.",
     "habitat": "Alp yaylovlari, 2500-3500m",
     "regions": "G'arbiy Tyan-Shan",
     "fine_bhm_min": 100, "fine_bhm_max": 300, "law_article": "Jinoiy 202-modda"},

    # ====== QUSHLAR ======
    {"slug": "chlamydotis-macqueenii", "name": "Johildqaldirg'och", "latin": "Chlamydotis macqueenii",
     "category": "qush", "icon_name": "paw", "red_book": True, "iucn_status": "VU",
     "summary": "Cho'l johildqaldirg'ochi. Noqonuniy ovdan xavfda.",
     "habitat": "Dasht-cho'l",
     "regions": "Qizilqum, Ustyurt",
     "fine_bhm_min": 200, "fine_bhm_max": 500, "law_article": "Jinoiy 202-modda"},

    {"slug": "aquila-heliaca", "name": "Qora burgut", "latin": "Aquila heliaca",
     "category": "qush", "icon_name": "paw", "red_book": True, "iucn_status": "VU",
     "summary": "Eng kuchli bo'yinbosar yirtqich qush.",
     "habitat": "Cho'l va tog' ostlari",
     "regions": "Butun UZ",
     "fine_bhm_min": 300, "fine_bhm_max": 700, "law_article": "Jinoiy 202-modda"},

    {"slug": "falco-cherrug", "name": "Lochin", "latin": "Falco cherrug",
     "category": "qush", "icon_name": "paw", "red_book": True, "iucn_status": "EN",
     "summary": "Ov qushi. Jahon bozorida noqonuniy sotiladi.",
     "habitat": "Tog' va dasht",
     "regions": "Barcha UZ",
     "fine_bhm_min": 500, "fine_bhm_max": 1000, "law_article": "Jinoiy 202-modda"},

    {"slug": "tetraogallus-himalayensis", "name": "Himalay oqtoshulari", "latin": "Tetraogallus himalayensis",
     "category": "qush", "icon_name": "paw", "red_book": True, "iucn_status": "LC",
     "summary": "Baland tog' qushi.",
     "habitat": "3000m+", "regions": "Pomir-Oloy",
     "fine_bhm_min": 150, "fine_bhm_max": 300, "law_article": "Jinoiy 202-modda"},

    # ====== HASHAROTLAR ======
    {"slug": "parnassius-apollo", "name": "Apollon kapalagi", "latin": "Parnassius apollo",
     "category": "hasharot", "icon_name": "paw", "red_book": True, "iucn_status": "VU",
     "summary": "Tog' kapalagi. Kolleksiyachilar tufayli kam.",
     "habitat": "Tog' yaylovlari",
     "regions": "Tog'li UZ",
     "fine_bhm_min": 30, "fine_bhm_max": 80, "law_article": "MK 204-modda"},

    {"slug": "carabus-shewbelskyi", "name": "Shevbelskiy qo'ng'izi", "latin": "Carabus shewbelskyi",
     "category": "hasharot", "icon_name": "paw", "red_book": True, "iucn_status": "VU",
     "summary": "Endemik yirtqich qo'ng'iz.",
     "habitat": "Tog' o'rmonlari",
     "regions": "Zarafshon",
     "fine_bhm_min": 20, "fine_bhm_max": 50, "law_article": "MK 204-modda"},

    # ====== SUDRALUVCHILAR ======
    {"slug": "varanus-griseus", "name": "Kulrang varan", "latin": "Varanus griseus",
     "category": "jonivor", "icon_name": "snake", "red_book": True, "iucn_status": "LC",
     "summary": "O'zbek cho'l drakonchasi. Yo'qolib borayapti.",
     "habitat": "Qizilqum",
     "regions": "Markaziy UZ",
     "fine_bhm_min": 80, "fine_bhm_max": 200, "law_article": "MK 204-modda"},

    {"slug": "testudo-horsfieldii", "name": "O'rta osiyo toshbaqasi", "latin": "Testudo horsfieldii",
     "category": "jonivor", "icon_name": "paw", "red_book": True, "iucn_status": "VU",
     "summary": "Brakonerlar tomonidan eksport uchun tutiladi.",
     "habitat": "Cho'l-dasht",
     "regions": "Barcha quruq UZ",
     "fine_bhm_min": 50, "fine_bhm_max": 120, "law_article": "MK 204-modda"},

    {"slug": "macrovipera-lebetina", "name": "O'rta Osiyo gurzasi", "latin": "Macrovipera lebetina",
     "category": "jonivor", "icon_name": "snake", "red_book": False, "iucn_status": "LC",
     "summary": "Zaharli ilon. Hayot uchun xavfli.",
     "warnings": "Hemotoksik zahar. 103'ga zudlik.",
     "first_aid": "Tinchlaning. Chaqqan joyni pastroq. 103. Kesmang, so'rmang.",
     "habitat": "Qoyali yon bag'irlar",
     "livestock_danger": "deadly",
     "regions": "Barcha tog'li UZ"},

    # ====== ASALBOP / DORIVOR / HALOL FILTERLAR UCHUN ======
    {"slug": "rhamnus-cathartica", "name": "Jumrut", "latin": "Rhamnus cathartica",
     "category": "daraxt", "icon_name": "tree", "red_book": False, "iucn_status": "LC",
     "summary": "Asalbop daraxt.",
     "is_honey_plant": True, "halal_status": "unknown",
     "regions": "Tog' yon bag'ri"},

    {"slug": "trifolium-pratense", "name": "Qizil sebarga", "latin": "Trifolium pratense",
     "category": "giyoh", "icon_name": "leaf", "red_book": False, "iucn_status": "LC",
     "summary": "Asalari uchun eng yaxshi giyoh.",
     "is_honey_plant": True, "is_edible": True, "halal_status": "halal",
     "uses": "Asalari nektar manbai. Oziq-ovqat uchun ham.",
     "bloom_months": "5,6,7",
     "regions": "Butun UZ"},

    {"slug": "origanum-vulgare", "name": "Tog' rayhon", "latin": "Origanum vulgare",
     "category": "giyoh", "icon_name": "leaf", "red_book": False, "iucn_status": "LC",
     "summary": "Tog' giyohi, dorivor.",
     "is_medicinal": True, "is_edible": True, "is_honey_plant": True,
     "halal_status": "halal",
     "uses": "Choy, damlama, ovqatga ziravor.",
     "bloom_months": "6,7,8",
     "regions": "Tog' yon bag'ri"},

    {"slug": "hyoscyamus-niger", "name": "Mingdevona", "latin": "Hyoscyamus niger",
     "category": "giyoh", "icon_name": "leaf", "red_book": False, "iucn_status": "LC",
     "summary": "Zaharli o't. Chorva uchun o'lim xavfli.",
     "livestock_danger": "deadly",
     "warnings": "Chorva yeydi → yoppasiga o'lim.",
     "first_aid": "Hayvon yegan bo'lsa darhol veterinarga.",
     "halal_status": "haram",
     "regions": "Dasht, cho'l"},

    {"slug": "ranunculus-sceleratus", "name": "Yuzanachiq", "latin": "Ranunculus sceleratus",
     "category": "giyoh", "icon_name": "leaf", "red_book": False, "iucn_status": "LC",
     "summary": "Chorva uchun zaharli.",
     "livestock_danger": "toxic", "halal_status": "haram",
     "regions": "Nam joylar"},
]


class Command(BaseCommand):
    help = "30+ real O'zbekiston Qizil kitob + filter tag'lar seed"

    def handle(self, *args, **opts):
        created = 0
        updated = 0
        for s in REDBOOK_DATA:
            obj, was_created = Species.objects.update_or_create(slug=s["slug"], defaults=s)
            if was_created:
                created += 1
            else:
                updated += 1
        total = Species.objects.count()
        red_count = Species.objects.filter(red_book=True).count()
        self.stdout.write(self.style.SUCCESS(
            f"✓ Seed: {created} yangi · {updated} yangilangan · jami {total} tur · {red_count} Qizil kitob"
        ))
