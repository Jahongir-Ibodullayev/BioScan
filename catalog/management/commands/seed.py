"""`python manage.py seed` — boshlang'ich ma'lumotlar."""
from django.core.management.base import BaseCommand

from catalog.models import Species

SEEDS = [
    {
        "slug": "isiriq",
        "name": "Isiriq",
        "latin": "Peganum harmala",
        "category": "giyoh",
        "icon_name": "leaf",
        "color_class": "bg-primary-100 text-primary-700",
        "red_book": True,
        "iucn_status": "LC",
        "summary": "Markaziy Osiyo tog'larida keng tarqalgan, shifobaxsh va zaharli xususiyatlarga ega ko'p yillik o'simlik.",
        "description": "Isiriq — Peganum harmala — xalq tabobatida asrlar davomida ishlatilib kelayotgan ko'p yillik o'simlik. Tog' yon bag'irlarida, qurg'oqchil dalalarda o'sadi. Urug'larida harmalin alkaloidi bor.",
        "habitat": "Qoyali yonbag'irlar, 600–1800 m balandlik, quruq tuproq.",
        "uses": "Tutatib xonani poklash, sovuq oldi profilaktikasi, tabiiy rangchilar uchun xom ashyo.",
        "warnings": "Katta miqdorda qabul qilinsa, gallyutsinatsiya va yurak ishi buzilishiga olib keladi.",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/94/Peganum_harmala_003.JPG/800px-Peganum_harmala_003.JPG",
        "regions": "Markaziy Osiyo, Shahrisabz tog'lari",
    },
    {
        "slug": "yovvoyi-yongoq",
        "name": "Yovvoyi yong'oq",
        "latin": "Juglans regia",
        "category": "daraxt",
        "icon_name": "tree",
        "color_class": "bg-amber-100 text-amber-700",
        "red_book": False,
        "iucn_status": "NT",
        "summary": "Tog' daralarida uchraydigan, mevasi to'yimli va shifobaxsh daraxt.",
        "description": "Yovvoyi yong'oq daraxti 25 metrgacha o'sadi, 300 yilgacha yashaydi. Mevasi oqsil va Omega-3 ga boy.",
        "habitat": "Nam daralar, soyali yonbag'irlar, 1200–2200 m.",
        "uses": "Meva ozuqa sifatida, yaprog'i — choy; yog'ochi qurilishda.",
        "regions": "O'zbekiston tog'lari, G'arbiy Tyan-Shan",
    },
    {
        "slug": "tog-archa",
        "name": "Tog' archa",
        "latin": "Juniperus communis",
        "category": "daraxt",
        "icon_name": "tree",
        "color_class": "bg-emerald-100 text-emerald-700",
        "red_book": True,
        "iucn_status": "LC",
        "summary": "Salomatlik uchun foydali havo beruvchi, yong'inga chidamli tog' daraxti.",
        "description": "Tog' archa o'ta sekin o'sadi, 500 yilgacha yashaydi. Efir moylari atrof havoni sterilizatsiya qiladi.",
        "habitat": "Tosh tuproq, shamolli cho'qqilar, 1500–3000 m.",
        "uses": "Efir moyi, havo poklash, manzarali o'rmon.",
        "warnings": "Shox-shabbasini kesish qat'iyan taqiqlanadi.",
        "regions": "G'arbiy Tyan-Shan, Pomir-Oloy",
    },
    {
        "slug": "qizil-lola",
        "name": "Qizil lola",
        "latin": "Tulipa greigii",
        "category": "gul",
        "icon_name": "flower",
        "color_class": "bg-rose-100 text-rose-700",
        "red_book": True,
        "iucn_status": "VU",
        "summary": "Bahorda tog'lar yon bag'rini qizilga bo'yaydi, Qizil kitobga kiritilgan.",
        "description": "Tulipa greigii O'zbekiston endemigi hisoblanadi. Aprel–may oylarida gullaydi.",
        "habitat": "Toshli dashtlar, 700–2500 m.",
        "warnings": "Terib olish — jarima. Faqat fotosuratga olish ruxsat etiladi.",
        "regions": "O'zbekiston endemigi",
    },
    {
        "slug": "orta-osiyo-gurzasi",
        "name": "O'rta Osiyo gurzasi",
        "latin": "Macrovipera lebetina",
        "category": "jonivor",
        "icon_name": "snake",
        "color_class": "bg-danger-light text-danger",
        "red_book": False,
        "iucn_status": "LC",
        "summary": "O'lkamizning eng zaharli ilonlaridan biri, qoyali joylarda faol.",
        "description": "O'rta Osiyo gurzasi 1.5 metrgacha uzunlikka yetadi. Issiq oylarda faol. Zahari hemotoksik.",
        "habitat": "Qoyali yonbag'irlar, tosh uyumlari, quruq dalalar, 300–2500 m.",
        "warnings": "Bosib qolmang. Ko'p hollarda kiyim bilan og'riqsiz chaqadi.",
        "first_aid": "1) Tinch bo'ling. 2) Chaqqan joyni pastroq tuting. 3) Ko'p suv iching. 4) 103 ga zudlik bilan qo'ng'iroq qiling. Kesmang, so'rmang.",
        "regions": "Markaziy Osiyo",
    },
    {
        "slug": "qora-chayon",
        "name": "Qora chayon",
        "latin": "Orthochirus scrobiculosus",
        "category": "hasharot",
        "icon_name": "paw",
        "color_class": "bg-slate-100 text-slate-700",
        "red_book": False,
        "iucn_status": "LC",
        "summary": "Tunda faol, qoyalar ostida yashiringan, kichik ammo og'riqli chayon.",
        "description": "Uzunligi 5–7 sm. Zahari asab tizimiga ta'sir qiladi.",
        "habitat": "Tosh ostlari, yoriqlar, quruq qumli joylar.",
        "first_aid": "Chaqqan joyni muzlatib, anti-gistamin tabletka ichib, shifokorga murojaat qiling.",
        "regions": "O'zbekiston janubi, Turkmaniston",
    },
]


class Command(BaseCommand):
    help = "Catalog uchun boshlang'ich turlarni qo'shish"

    def handle(self, *args, **opts):
        created = 0
        for s in SEEDS:
            obj, was_created = Species.objects.update_or_create(slug=s["slug"], defaults=s)
            if was_created:
                created += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Seed done · {created} yangi · {len(SEEDS) - created} yangilangan · jami {Species.objects.count()}"
            )
        )
