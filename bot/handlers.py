"""Telegram bot handlers."""
import logging
import urllib.parse

from telegram import Update, InputMediaPhoto
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from . import formatters, keyboards
from .service import get_species, pick_species_for_photo

log = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Commands
# ------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        formatters.welcome_text(user.first_name or "Do'stim"),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboards.main_menu(),
    )
    await update.message.reply_text(
        "Quyidagi tugmalardan birini tanlang yoki rasm yuboring:",
        reply_markup=keyboards.start_keyboard(),
    )


async def app_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open the web app directly."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🌿 Tog'AI ilovasini ochish",
            web_app=WebAppInfo(url="https://startup-seven-pied.vercel.app"),
        )
    ]])
    await update.message.reply_text(
        "🌿 <b>Tog'AI — Tabiatingni kashf qil</b>\n\n"
        "To'liq web-ilovadan foydalaning: AI skaner, Qizil kitob, xarita, namoz vaqti, chat…",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 <b>Yordam</b>\n\n"
        "• Rasm yuboring — AI turni aniqlaydi\n"
        "• /app — web ilovani ochish\n"
        "• /start — menyu\n"
        "• /sos — favqulodda yordam\n"
        "• 103 — tibbiy favqulodda\n",
        parse_mode=ParseMode.HTML,
    )


async def emergency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚨 <b>FAVQULODDA</b>\n\n"
        "📞 <b>103</b> — Tibbiy yordam\n"
        "📞 <b>101</b> — Yong'in xizmati\n"
        "📞 <b>102</b> — Militsiya\n"
        "📞 <b>112</b> — Yagona xizmat\n\n"
        "Ilon chaqdi? Kesmang, so'rmang. Tinch yoting, 103 ga qo'ng'iroq qiling.",
        parse_mode=ParseMode.HTML,
    )


# ------------------------------------------------------------------
# Photo handler (main flow)
# ------------------------------------------------------------------
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)

    # 1. Show analyzing status
    thinking = await update.message.reply_text(
        formatters.analyzing_text(),
        parse_mode=ParseMode.HTML,
    )

    # 2. Run AI (mock)
    species, confidence = await pick_species_for_photo()

    if species is None:
        await thinking.edit_text(
            "❌ Ma'lumotlar bazasi bo'sh. Iltimos, administrator bilan bog'laning."
        )
        return

    # 3. Prepare response
    caption = formatters.species_caption(species, confidence)
    ytq = urllib.parse.quote(f"{species.name} {species.latin}")
    reply_markup = keyboards.species_inline(species.slug, ytq)

    # 4. Send species photo with full caption + inline buttons
    try:
        if species.image and species.image.name:
            # Use uploaded image if exists
            with species.image.open("rb") as f:
                await update.message.reply_photo(
                    photo=f,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup,
                )
        elif species.image_url:
            await update.message.reply_photo(
                photo=species.image_url,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
            )
        else:
            await update.message.reply_text(
                caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup
            )
    except Exception as e:
        log.warning("photo send failed, falling back to text: %s", e)
        await update.message.reply_text(
            caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup
        )

    # 5. Clean up thinking placeholder
    try:
        await thinking.delete()
    except Exception:
        pass


# ------------------------------------------------------------------
# Text / main-menu buttons
# ------------------------------------------------------------------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    base = "https://startup-seven-pied.vercel.app"

    MAP = {
        "🌿 Tog'AI ilovasini ochish": f"🌿 Web ilova: {base}",
        "📷 Skaner": f"📸 Skaner: rasm yuboring yoki web ilovada oching — {base}/app/scanner",
        "📚 Katalog": f"📚 Katalog: {base}/app/catalog",
        "🗺 Xarita": f"🗺 Xarita: {base}/app/map",
        "🤖 AI yordam": "Savolingizni yozing — AI javob beradi. Yoki rasm yuboring 📷",
        "🏅 Herbariy": f"🏅 Kolleksiyangiz: {base}/app/collection",
        "⚠️ Hodisa xabar": f"⚠️ Hodisa: {base}/app/report yoki /sos",
    }
    if text in MAP:
        await update.message.reply_text(MAP[text])
        return

    # AI fallback — free-form questions answered by LLM
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    try:
        from togai.integrations import groq_chat
        system = (
            "Sen Tog'AI yordamchisisan — Markaziy Osiyo flora/faunasi bo'yicha ekspert biologist. "
            "O'zbek tilida qisqa (3-5 jumla), aniq, amaliy javob ber. "
            "Xavfli mavzularda ehtiyot choralarini ko'rsat. "
            "Agar bilmasang 'Ma'lumot yetarli emas' deb yoz — taxmin qilma."
        )
        reply = groq_chat(text, system=system)
        await update.message.reply_text(reply)
    except Exception as e:
        log.exception("AI chat error in bot")
        await update.message.reply_text(
            "🤖 Hozir javob bera olmadim. Qayta urinib ko'ring yoki rasm yuboring 📷"
        )


# ------------------------------------------------------------------
# Callback queries (inline buttons)
# ------------------------------------------------------------------
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data or ""

    # Tabs
    if data.startswith("tab:"):
        _, tab, slug = data.split(":", 2)
        species = await get_species(slug)
        if not species:
            return
        await q.message.reply_text(
            formatters.tab_content(species, tab),
            parse_mode=ParseMode.HTML,
            reply_markup=keyboards.back_to_card(slug),
        )
        return

    # AI menu
    if data.startswith("ai:menu:"):
        slug = data.split(":", 2)[2]
        species = await get_species(slug)
        if not species:
            return
        await q.message.reply_text(
            f"🌟 <b>AI dan {species.name} haqida so'rang</b>\n\nSavolni tanlang:",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboards.ai_questions_menu(slug),
        )
        return

    # AI answer
    if data.startswith("ai:ask:"):
        parts = data.split(":", 3)
        kind, slug = parts[2], parts[3]
        species = await get_species(slug)
        if not species:
            return
        await q.message.reply_text(
            formatters.ai_answer(species, kind),
            parse_mode=ParseMode.HTML,
            reply_markup=keyboards.back_to_card(slug),
        )
        return

    # Save to collection
    if data.startswith("save:"):
        slug = data.split(":", 1)[1]
        await q.answer("Kolleksiyangizga qo'shildi! 💾", show_alert=True)
        return

    # Back / show original card
    if data.startswith("back:"):
        slug = data.split(":", 1)[1]
        species = await get_species(slug)
        if not species:
            return
        ytq = urllib.parse.quote(f"{species.name} {species.latin}")
        await q.message.reply_text(
            formatters.species_caption(species),
            parse_mode=ParseMode.HTML,
            reply_markup=keyboards.species_inline(slug, ytq),
        )
        return

    # Hints
    if data == "hint:photo":
        await q.message.reply_text("📸 O'simlik yoki jonivor rasmini yuboring — AI 2 soniyada aniqlaydi.")
        return
    if data == "cmd:catalog":
        await q.message.reply_text("📚 Katalog: https://togai.uz/app/catalog")
        return
    if data == "cmd:chat":
        await q.message.reply_text("🤖 AI chat: https://togai.uz/app/chat")
        return


# ------------------------------------------------------------------
# Error handler
# ------------------------------------------------------------------
async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.exception("bot error: %s", context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ Xatolik yuz berdi. Yaqin orada to'g'irlaymiz.\nBoshqa rasm yuborib ko'ring yoki /start ni bosing."
            )
        except Exception:
            pass


# Re-exported InputMediaPhoto for completeness (unused but type-available)
__all__ = [
    "start",
    "help_cmd",
    "emergency",
    "photo_handler",
    "text_handler",
    "callback_handler",
    "on_error",
    "InputMediaPhoto",
]
