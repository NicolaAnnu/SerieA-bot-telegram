from datetime import timedelta
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from .config import TELEGRAM_TOKEN, FOOTBALL_DATA_TOKEN, GROUP_CHAT_ID
from .handlers import (
    start,
    partitedefault,
    chatid,
    status,
    comandi,
    classifica_handler,
    partite_handler,
)
from .scheduler import check_and_schedule, _post_init


def main():
    if not TELEGRAM_TOKEN or not FOOTBALL_DATA_TOKEN or not GROUP_CHAT_ID:
        raise SystemExit("Config mancante: controlla TELEGRAM_TOKEN, FOOTBALL_DATA_TOKEN, GROUP_CHAT_ID nel .env")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("partite", partitedefault))
    app.add_handler(CommandHandler("chatid", chatid))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("comandi", comandi))
    app.add_handler(CommandHandler("classifica", classifica_handler))
    app.add_handler(MessageHandler(filters.Regex(r"^/partite\d{1,2}\b"), partite_handler))
    app.add_handler(CommandHandler("partite", partite_handler))  

    app.job_queue.run_repeating(check_and_schedule, interval=timedelta(days=1), first=timedelta(hours=6))
    app.post_init = _post_init

    app.run_polling()