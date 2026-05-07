"""Message formatters for the BioScan bot."""
from catalog.models import Species


CAT_LABEL = {
    "giyoh": "Giyoh",
    "daraxt": "Daraxt",
    "gul": "Gul",
    "jonivor": "Jonivor",
    "hasharot": "Hasharot",
    "qush": "Qush",
    "qoziqorin": "Qoziqorin",
}

IUCN_LABEL = {
    "LC": "🟢 Eng kam tashvish",
    "NT": "🟡 Qisman xavfli",
    "VU": "🟠 Zaif",
    "EN": "🔴 Xavf ostida",
    "CR": "⛔️ Yo'qolib borayotgan",
    "EW": "⚫️ Yovvoyida yo'q",
    "EX": "☠️ Yo'qolib ketgan",
    "DD": "⚪️ Ma'lumot yo'q",
    "NE": "— Baholanmagan",
}


def species_caption(s: Species, confidence: float = 0.98) -> str:
    """Telegram caption with minimal HTML formatting."""
    red = "🏅 <b>Qizil kitob</b>" if s.red_book else ""
    category = CAT_LABEL.get(s.category, s.category.title())
    status = IUCN_LABEL.get(s.iucn_status, s.iucn_status)

    lines = [
        f"<b>{s.name}</b>  ·  <i>{s.latin}</i>",
        f"{category} · AI aniqlik: <b>{confidence*100:.0f}%</b>",
        "",
    ]
    if red:
        lines.append(f"{red}")
    lines.append(f"🌍 Status: {status}")
    if s.regions:
        lines.append(f"📍 Mintaqa: {s.regions}")
    lines.append("")
    if s.summary:
        lines.append(s.summary)
    lines.append("")
    lines.append("👇 Pastdagi tugmalar orqali batafsil ma'lumot oling")
    return "\n".join(lines)


def tab_content(s: Species, tab: str) -> str:
    # First aid faqat haqiqiy xavfli turlarda 103 ko'rsatadi
    # (zaharli o'simlik, ilon, chayon va h.k. — bot/AI 'first_aid' to'ldirishi kerak)
    DANGEROUS_KEYWORDS = ("ilon", "snake", "vipera", "naja", "echis", "chayon", "scorpion",
                          "zaharli", "toxic", "poison", "yirtqich", "predator",
                          "alkaloid", "saponin")
    is_dangerous = (
        bool(s.first_aid)
        or s.category in ("ilon", "reptile", "insect", "hasharot")
        or any(kw in (s.warnings or "").lower() for kw in DANGEROUS_KEYWORDS)
        or any(kw in (s.name or "").lower() for kw in DANGEROUS_KEYWORDS)
    )
    if is_dangerous:
        firstaid_text = s.first_aid or "Birinchi yordam zarurati bo'lsa — 103 ga qo'ng'iroq qiling."
    else:
        firstaid_text = (
            f"<b>{s.name}</b> xavfsiz tur. Birinchi yordam talab qilinmaydi.\n\n"
            "Lekin agar allergiya yoki noqulay reaksiya sezsangiz — shifokor bilan maslahatlashing."
        )

    mapping = {
        "general": ("📖 Umumiy ma'lumot", s.description or s.summary or "Ma'lumot yo'q."),
        "uses": ("✨ Foydasi", s.uses or "Bu tur uchun foyda ma'lumotlari hozircha bazaga qo'shilmagan."),
        "warnings": ("⚠️ Xavfi va ehtiyot choralari", s.warnings or "Ma'lum xavf aniqlanmagan. Tur xavfsiz hisoblanadi."),
        "firstaid": ("🚑 Birinchi yordam", firstaid_text),
    }
    title, body = mapping.get(tab, ("—", "Topilmadi"))
    return f"<b>{s.name}</b> — <i>{s.latin}</i>\n\n<b>{title}</b>\n\n{body}"


def ai_answer(s: Species, kind: str) -> str:
    """Canned-but-contextual AI-style answers. Real AI later."""
    base = f"<b>{s.name}</b> — <i>{s.latin}</i>\n\n"
    answers = {
        "prep": (
            f"🍵 <b>Tayyorlash usullari</b>\n\n"
            f"• <b>Choy</b>: 1 osh qoshiq quritilgan {s.name}ni 200 ml qaynoq suvda 10 daqiqa damlang. Kuniga 2 marta iching.\n"
            f"• <b>Kompress</b>: yangi barglarini yanchib, zararlangan joyga 15 daqiqa qo'ying.\n"
            f"• <b>Tutatish</b>: quruq barglarini olovda tutating — havoni tozalaydi.\n\n"
            f"⚠️ Dozalash shifokor bilan kelishilishi shart."
        ),
        "benefits": (
            f"💊 <b>Foydalari</b>\n\n{s.uses or s.summary or 'Umumiy shifobaxsh xususiyatlariga ega.'}\n\n"
            f"📚 Qo'shimcha ilmiy manbalar uchun ⬇️ Wikipedia/iNaturalist tugmalarini bosing."
        ),
        "cure": (
            f"🩺 <b>Qanday kasalliklarga yaxshi?</b>\n\n"
            f"An'anaviy tabobat bo'yicha {s.name} quyidagilarga yordam berishi mumkin:\n"
            f"• Sovuq oldi profilaktikasi\n"
            f"• Hazm tizimini yaxshilash\n"
            f"• Terining ozgina shikastlanishi\n\n"
            f"⚕️ <b>Diqqat</b>: Har qanday jiddiy muammo uchun avval shifokorga murojaat qiling."
        ),
        "precaution": (
            f"⚠️ <b>Ehtiyot choralari</b>\n\n{s.warnings or 'Jiddiy xavf aniqlanmagan, ammo e’tibor bering:'}\n\n"
            f"• Homilador va emizikli ayollar uchun tavsiya qilinmaydi\n"
            f"• Allergiya bo'lsa — iste'mol qilmang\n"
            f"• Bolalarda faqat shifokor nazoratida qo'llang"
        ),
        "custom": (
            "✍️ <b>O'z savolingizni yozing</b>\n\n"
            f"Shu xabarga javob qilib ({s.name} haqidagi) savolingizni yuboring — AI yordamchim javob beradi.\n\n"
            "Misol: «Yozgi issiq havoda qanday saqlash kerak?»"
        ),
    }
    return base + answers.get(kind, "Javob tayyorlanyapti...")


def welcome_text(user_first_name: str) -> str:
    return (
        f"Assalomu alaykum, <b>{user_first_name}</b>! 🌿\n\n"
        "Men — <b>BioScan</b> botiman. Tabiatni tanib, xavfsiz bo'lishingizga yordam beraman.\n\n"
        "<b>Nima qila olaman:</b>\n"
        "📷 O'simlik/hayvon rasmini yuboring — 2 soniyada aniqlayman\n"
        "📚 Qizil kitob va foydali giyohlar bazasi\n"
        "🤖 AI yordamchi — istalgan savolga javob\n"
        "🗺 Xarita va xavf zonalari\n"
        "▶️ YouTube darslar va ilmiy manbalar\n\n"
        "<b>Hoziroq boshlang</b> — rasm yuboring 👇"
    )


def analyzing_text() -> str:
    return (
        "🔬 <b>Rasm tahlil qilinyapti...</b>\n\n"
        "• Rang va shakl tahlil qilinmoqda\n"
        "• Ma'lumotlar bazasida qidirilmoqda\n"
        "• AI xulosa chiqaryapti...\n\n"
        "<i>2 soniyada tayyor bo'ladi.</i>"
    )
