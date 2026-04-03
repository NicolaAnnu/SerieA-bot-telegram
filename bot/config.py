import logging
import os
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

# ----------------- Config -----------------
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
FOOTBALL_DATA_TOKEN = os.getenv("FOOTBALL_DATA_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID", "0"))

# Europe/Rome
TZ_LOCAL = ZoneInfo("Europe/Rome")

# Logging base
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("seriea-bot")