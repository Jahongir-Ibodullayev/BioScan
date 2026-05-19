"""BioScan Telegram bot — /login flow + welcome.

Django'ning bot/ app teng portasi. python-telegram-bot v21+ (asinxron).

Ishga tushirish:
    ./venv/bin/python -m app.bot.run

Yoki systemd unit (bioscan-bot.service).
"""
from __future__ import annotations

import logging
import sys

from sqlalchemy import select
from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.core.config import settings
from app.db.session import _get_sessionmaker
from app.models.user import User

log = logging.getLogger("bioscan-bot")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


WELCOME = (
    "👋 Salom! Men <b>BioScan</b> botiman.\n\n"
    "Tabiatdagi tur (giyoh, gul, jonivor, hasharot)ni aniqlash uchun "
    "ilovamizdan foydalaning: https://bioscan.duckdns.org\n\n"
    "Kirish uchun /login yuboring."
)

LOGIN_PROMPT = (
    "📱 Telefon raqamingizni ulashish uchun pastdagi tugmani bosing.\n\n"
    "Hisobingiz Telegram'ga bog'lanadi (xabarlar uchun). "
    "Ilovaga kirish — telefon raqam va parol bilan."
)


async def cmd_start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME, parse_mode="HTML", disable_web_page_preview=True)


async def cmd_login(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Telefon raqamni ulashish", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True,
    )
    await update.message.reply_text(LOGIN_PROMPT, reply_markup=kb)


async def on_contact(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if not contact or not contact.phone_number:
        return
    phone = contact.phone_number.strip()
    if not phone.startswith("+"):
        phone = "+" + phone

    tg_user = update.effective_user
    sm = _get_sessionmaker()
    async with sm() as db:
        user = await db.scalar(select(User).where(User.phone == phone))
        if user is None:
            user = User(
                phone=phone,
                password="",
                full_name=" ".join(filter(None, [tg_user.first_name, tg_user.last_name])) or "",
                telegram_id=tg_user.id,
                telegram_username=tg_user.username or "",
                is_active=True,
            )
            db.add(user)
        else:
            user.telegram_id = tg_user.id
            user.telegram_username = tg_user.username or ""
        await db.commit()

    await update.message.reply_text(
        f"✅ Raqam <code>{phone}</code> bog'landi!\n\n"
        "Endi ilovaga kiring: https://bioscan.duckdns.org\n"
        "Telefon raqam va parol bilan kirasiz.",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


async def cmd_help(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start — boshlash\n"
        "/login — Telegram orqali kirish\n"
        "/help — yordam\n\n"
        "Webapp: https://bioscan.duckdns.org",
        disable_web_page_preview=True,
    )


def main():
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        log.error("TELEGRAM_BOT_TOKEN .env'da yo'q")
        sys.exit(1)

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("login", cmd_login))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.CONTACT, on_contact))

    log.info("Bot ishga tushdi — @%s", settings.TELEGRAM_BOT_USERNAME)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
