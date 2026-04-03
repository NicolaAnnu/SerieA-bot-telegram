from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from .config import GROUP_CHAT_ID, TZ_LOCAL
from .constants import giorni, mesi

def formatta_it(dt):
    dt = dt.astimezone(TZ_LOCAL)
    g = giorni[dt.strftime("%A")]
    m = mesi[dt.strftime("%B")]
    return f"{g} {dt.strftime('%d')} {m} {dt.strftime('%Y, %H:%M')}"

def fmt_row(row, name_width=18):
    pos = row.get("position", 0)
    team = (row.get("team", {}) or {}).get("shortName") or (row.get("team", {}) or {}).get("name", "—")
    played = row.get("playedGames", 0)
    won = row.get("won", 0)
    draw = row.get("draw", 0)
    lost = row.get("lost", 0)
    pts = row.get("points", 0)

    team = (team[:name_width]).ljust(name_width)
    return f"{pos:>2}  {team}  {pts:>3} {played:>3} {won:>3} {draw:>3} {lost:>3}"

async def send_text_safe(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    chat_id = update.effective_chat.id if update and update.effective_chat else GROUP_CHAT_ID
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )