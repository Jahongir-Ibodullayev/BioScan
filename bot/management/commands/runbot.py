"""`python manage.py runbot` — Telegram bot'ni ishga tushirish."""
import logging

from decouple import config
from django.core.management.base import BaseCommand, CommandError
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from bot import handlers


class Command(BaseCommand):
    help = "BioScan Telegram botini ishga tushirish (uzoq-polling rejimida)"

    def handle(self, *args, **opts):
        token = config("TELEGRAM_BOT_TOKEN", default=None)
        if not token:
            raise CommandError(
                "TELEGRAM_BOT_TOKEN o'rnatilmagan. .env faylga qo'shing:\n"
                "  TELEGRAM_BOT_TOKEN=123:ABC-...\n"
                "Token olish uchun: @BotFather"
            )

        logging.basicConfig(
            format="%(asctime)s · %(levelname)s · %(name)s · %(message)s",
            level=logging.INFO,
        )

        app = ApplicationBuilder().token(token).build()

        # Commands
        app.add_handler(CommandHandler("start", handlers.start))
        app.add_handler(CommandHandler("help", handlers.help_cmd))
        app.add_handler(CommandHandler("app", handlers.app_cmd))
        app.add_handler(CommandHandler("sos", handlers.emergency))
        app.add_handler(CommandHandler("xavf", handlers.emergency))
        app.add_handler(CommandHandler("emergency", handlers.emergency))

        # Photo
        app.add_handler(MessageHandler(filters.PHOTO, handlers.photo_handler))

        # /login va contact handler olib tashlandi — webapp endi telefon+parol bilan ishlaydi.

        # Callback queries (inline buttons)
        app.add_handler(CallbackQueryHandler(handlers.callback_handler))

        # Text / menu buttons
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.text_handler))

        # Errors
        app.add_error_handler(handlers.on_error)

        self.stdout.write(self.style.SUCCESS("🤖 BioScan bot ishga tushdi — polling..."))
        app.run_polling(allowed_updates=["message", "callback_query", "contact"])
