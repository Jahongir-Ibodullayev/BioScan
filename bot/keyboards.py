"""Inline keyboards for Tog'AI Telegram bot."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


def main_menu() -> ReplyKeyboardMarkup:
    """Main persistent menu at bottom."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📷 Skaner"), KeyboardButton("📚 Katalog")],
            [KeyboardButton("🗺 Xarita"), KeyboardButton("🤖 AI yordam")],
            [KeyboardButton("🏅 Herbariy"), KeyboardButton("⚠️ Hodisa xabar")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Menyudan tanlang yoki rasm yuboring…",
    )


def species_inline(slug: str, youtube_q: str, lat: float | None = None, lng: float | None = None) -> InlineKeyboardMarkup:
    """Under-caption inline keyboard for a species card."""
    rows = [
        [
            InlineKeyboardButton("📖 Umumiy", callback_data=f"tab:general:{slug}"),
            InlineKeyboardButton("✨ Foydasi", callback_data=f"tab:uses:{slug}"),
        ],
        [
            InlineKeyboardButton("⚠️ Xavfi", callback_data=f"tab:warnings:{slug}"),
            InlineKeyboardButton("🚑 Birinchi yordam", callback_data=f"tab:firstaid:{slug}"),
        ],
        [InlineKeyboardButton("🌟 AI dan so'rash", callback_data=f"ai:menu:{slug}")],
        [
            InlineKeyboardButton("▶️ YouTube darslar", url=f"https://www.youtube.com/results?search_query={youtube_q}"),
            InlineKeyboardButton("📚 Wikipedia", url=f"https://uz.wikipedia.org/wiki/{slug.replace('-', '_')}"),
        ],
        [
            InlineKeyboardButton("🔬 iNaturalist", url=f"https://www.inaturalist.org/search?q={youtube_q}"),
            InlineKeyboardButton("🌍 GBIF", url=f"https://www.gbif.org/species/search?q={youtube_q}"),
        ],
        [
            InlineKeyboardButton("💾 Kolleksiyaga saqlash", callback_data=f"save:{slug}"),
            InlineKeyboardButton("📤 Ulashish", switch_inline_query=f"Tog'AI: {youtube_q}"),
        ],
    ]
    if lat is not None and lng is not None:
        rows.insert(-1, [
            InlineKeyboardButton("📍 Xaritada ko'rish", url=f"https://www.google.com/maps?q={lat},{lng}")
        ])
    return InlineKeyboardMarkup(rows)


def ai_questions_menu(slug: str) -> InlineKeyboardMarkup:
    """AI quick-ask presets."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🍵 Qanday tayyorlash mumkin?", callback_data=f"ai:ask:prep:{slug}")],
            [InlineKeyboardButton("💊 Nima foydasi bor?", callback_data=f"ai:ask:benefits:{slug}")],
            [InlineKeyboardButton("🩺 Qaysi kasallikka yaxshi?", callback_data=f"ai:ask:cure:{slug}")],
            [InlineKeyboardButton("⚠️ Ehtiyot choralari?", callback_data=f"ai:ask:precaution:{slug}")],
            [InlineKeyboardButton("✍️ Boshqa savolingiz", callback_data=f"ai:ask:custom:{slug}")],
            [InlineKeyboardButton("⬅️ Orqaga", callback_data=f"back:{slug}")],
        ]
    )


def back_to_card(slug: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Asosiy ma'lumotga qaytish", callback_data=f"back:{slug}")]]
    )


def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📷 Rasm yuboring", callback_data="hint:photo")],
            [InlineKeyboardButton("📚 Katalog ko'rish", callback_data="cmd:catalog")],
            [InlineKeyboardButton("🤖 AI yordamchi", callback_data="cmd:chat")],
            [InlineKeyboardButton("🌐 Web ilovani ochish", url="https://togai.uz/app")],
        ]
    )
