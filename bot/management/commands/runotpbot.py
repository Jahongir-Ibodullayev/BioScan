"""`python manage.py runotpbot` — OTP yuborish uchun alohida Telegram bot.

Asosiy bot (skaner, chat, qidiruv) bilan aralashmaslik uchun bu yerda
faqat 3 ta handler ishlaydi:
  - /start  — qisqa salom + /login chaqiriqi
  - /login  — telefon raqami so'raydi (request_contact)
  - contact — kelgan raqamni User.telegram_id ga bog'laydi

Backend OTP yuborayotganda `TELEGRAM_OTP_BOT_TOKEN` ishlatadi (alohida bot).
"""
import logging

from decouple import config
from django.core.management.base import BaseCommand, CommandError
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot import handlers


async def otp_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """OTP bot uchun maxsus salomlash."""
    await update.message.reply_text(
        "🔐 <b>BioScan OTP boti</b>\n\n"
        "Bu bot orqali BioScan veb-ilovasiga (yoki ilovaga) kirayotganingizda "
        "tasdiqlash kodlari shu yerga keladi.\n\n"
        "▶ <b>Boshlash uchun</b>: /login bosing va telefon raqamingizni ulashing.",
        parse_mode=ParseMode.HTML,
    )


class Command(BaseCommand):
    help = "BioScan OTP botini ishga tushirish (kodlar yuborish uchun alohida)"

    def handle(self, *args, **opts):
        token = config("TELEGRAM_OTP_BOT_TOKEN", default=None)
        if not token:
            raise CommandError(
                "TELEGRAM_OTP_BOT_TOKEN o'rnatilmagan. .env faylga qo'shing:\n"
                "  TELEGRAM_OTP_BOT_TOKEN=8607...\n"
                "Token olish uchun: @BotFather"
            )

        logging.basicConfig(
            format="%(asctime)s · %(levelname)s · %(name)s · %(message)s",
            level=logging.INFO,
        )

        app = ApplicationBuilder().token(token).build()

        # Faqat 3 ta handler — minimum
        app.add_handler(CommandHandler("start", otp_start))
        app.add_handler(CommandHandler("login", handlers.login_cmd))
        app.add_handler(MessageHandler(filters.CONTACT, handlers.contact_handler))

        # Ixtiyoriy /help — qulaylik uchun
        async def otp_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text(
                "🔐 OTP bot — webapp/APK kirishida tasdiqlash kodlari shu yerga keladi.\n\n"
                "/login — telefon raqami ulash\n"
                "/start — qaytadan boshlash"
            )
        app.add_handler(CommandHandler("help", otp_help))

        # Errors
        app.add_error_handler(handlers.on_error)

        self.stdout.write(self.style.SUCCESS(
            "🔐 BioScan OTP bot ishga tushdi — polling..."
        ))
        app.run_polling(allowed_updates=["message", "contact"])
