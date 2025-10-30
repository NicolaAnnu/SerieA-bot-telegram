import asyncio
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes
import os, json
from typing import Optional
from telegram.constants import ParseMode

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "bot_state.json")

def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)
def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)

# ----------------- Config -----------------
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
FOOTBALL_DATA_TOKEN = os.getenv("FOOTBALL_DATA_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID", "0"))

# Europe/Rome per orari umani, UTC per sicurezza logica
TZ_LOCAL = ZoneInfo("Europe/Rome")

# Logging base
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("seriea-bot")


# ----------------- API Serie A -----------------
def fetch_first_kickoff_for_md(md: int) -> Optional[datetime]:
    """
    Ritorna il PRIMO kickoff (UTC, aware) della giornata md (1..38), considerando TUTTE le partite
    di quella giornata (FINISHED/IN_PLAY/TIMED/SCHEDULED). Se non trova partite, None.
    """
    url = "https://api.football-data.org/v4/competitions/SA/matches"
    headers = {"X-Auth-Token": FOOTBALL_DATA_TOKEN}
    params = {"matchday": md}  # niente 'status' -> tutte le partite della giornata
    r = requests.get(url, headers=headers, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    kickoffs = []
    for m in data.get("matches", []):
        utc_str = m.get("utcDate")
        if not utc_str:
            continue
        dt_utc = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        kickoffs.append(dt_utc)

    if not kickoffs:
        return None
    return min(kickoffs)


async def schedule_next_round(app: Application) -> None:
    """
    Notifica UNA SOLA VOLTA per giornata:
    - Trova la prossima giornata con MD > last_notified_matchday.
    - Calcola il PRIMO calcio d'inizio di quella giornata (anche se alcune partite sono già finite).
    - Se la finestra 30' prima è già passata (o la partita è iniziata), marca la giornata e passa oltre.
    - Altrimenti pianifica la notifica esattamente a T-30'.
    """
    try:
        state = load_state()
        last_md = int(state.get("last_notified_matchday", 0))  # es.: 8 => prossima candidabile è 9
        now_utc = datetime.now(timezone.utc)

        # 1) Trova la prossima giornata con partite future (usiamo SCHEDULED solo per sapere quali MD esistono nel futuro)
        url = "https://api.football-data.org/v4/competitions/SA/matches"
        headers = {"X-Auth-Token": FOOTBALL_DATA_TOKEN}
        params = {"status": "SCHEDULED"}
        r = requests.get(url, headers=headers, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()

        future_mds = sorted({int(m["matchday"]) for m in data.get("matches", [])
                             if m.get("matchday") is not None and 1 <= int(m["matchday"]) <= 38})
        # Filtra solo quelle > last_md
        future_mds = [md for md in future_mds if md > last_md]

        if not future_mds:
            logger.info("Nessuna giornata futura oltre MD%s. Riprovo tra 1 giorno.", last_md)
            app.job_queue.run_once(check_and_schedule, when=timedelta(days=1))
            return

        # 2) Scorri le giornate candidate finché non trovi una con 'primo kickoff' ancora utile
        planned = False
        for md in future_mds:
            first_kickoff = fetch_first_kickoff_for_md(md)
            if not first_kickoff:
                logger.info("MD%s non ha partite (API). Continuo con la successiva.", md)
                continue

            notify_utc = first_kickoff - timedelta(minutes=30)

            if now_utc >= first_kickoff:
                # il PRIMO match della giornata è già iniziato → questa giornata NON va notificata
                logger.info("MD%s: primo kickoff %s già iniziato. Marco come notificata e passo oltre.",
                            md, first_kickoff.isoformat())
                state["last_notified_matchday"] = md
                save_state(state)
                continue

            if now_utc >= notify_utc:
                # finestra T-30' già passata ma primo kickoff non è ancora iniziato → NON notificare (regola tua)
                logger.info("MD%s: finestra T-30' (%s) già passata. Salto giornata e passo oltre.",
                            md, notify_utc.isoformat())
                state["last_notified_matchday"] = md
                save_state(state)
                continue

            # 3) Pianifica T-30' del PRIMO match della giornata md
            for job in app.job_queue.get_jobs_by_name("md_notify"):
                job.schedule_removal()

            app.job_queue.run_once(
                send_lineups_reminder,
                when=notify_utc,
                name="md_notify",
                data={"matchday": md, "kickoff_utc": first_kickoff},
            )

            local_kick = first_kickoff.astimezone(TZ_LOCAL).strftime("%A %d %B %Y, %H:%M")
            local_notify = notify_utc.astimezone(TZ_LOCAL).strftime("%A %d %B %Y, %H:%M")
            logger.info("Pianificata NOTIFICA (una sola) per MD%s alle %s (local). Primo kickoff: %s (local).",
                        md, local_notify, local_kick)

            planned = True
            break  # abbiamo pianificato: fermati qui

        if not planned:
            # Tutte le giornate future hanno 'primo kickoff' con finestra T-30' già passata → riprova fra poco
            logger.info("Nessuna MD pianificabile (finestra già passata). Nuovo check tra 2 ore.")
            app.job_queue.run_once(check_and_schedule, when=timedelta(hours=2))

    except Exception as e:
        logger.exception("Errore nel planning: %s", e)
        app.job_queue.run_once(check_and_schedule, when=timedelta(hours=2))

async def check_and_schedule(context: ContextTypes.DEFAULT_TYPE) -> None:
    await schedule_next_round(context.application)


async def send_lineups_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    data = context.job.data or {}
    md = int(data.get("matchday"))
    kickoff_utc = data.get("kickoff_utc")

    kickoff_local = kickoff_utc.astimezone(TZ_LOCAL).strftime("%d/%m %H:%M")
    text = (
        f"Salve sono Angelo Ranieri il bot, sono qui per ricordarvi che\n"
        f"bisogna pubblicare la FORMAZIONE!!\n"
        f"Tra 30 minuti inizia la *Giornata {md}* di Serie A "
        f"(primo calcio d'inizio alle *{kickoff_local}*).\n\n"
        f"Pubblicate la formazione ora! "
    )

    try:
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
        logger.info(f"Messaggio inviato per MD{md}.")
    except Exception as e:
        logger.exception("Errore nell'invio messaggio: %s", e)

    
    state = load_state()
    state["last_notified_matchday"] = md
    save_state(state)
    logger.info(f"MD{md} registrata come notificata ")

    # ⏭️ Pianifica la prossima giornata
    await schedule_next_round(context.application)


# ----------------- Comandi utili -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
   await send_text_safe(
    update, 
    context, 
    "Ciao! Pianificherò un promemoria 30' prima della prossima giornata di Serie A. "
    "Usa /status per i dettagli."
)

async def chatid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cid = update.effective_chat.id
    await send_text_safe(update, context, f"Chat ID: `{cid}`")


async def send_text_safe(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    chat_id = update.effective_chat.id if update and update.effective_chat else GROUP_CHAT_ID
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )
    
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        state = load_state()
        last_md = int(state.get("last_notified_matchday", 0))

        # trova le prossime giornate con partite future
        url = "https://api.football-data.org/v4/competitions/SA/matches"
        headers = {"X-Auth-Token": FOOTBALL_DATA_TOKEN}
        params = {"status": "SCHEDULED"}
        r = requests.get(url, headers=headers, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()

        future_mds = sorted({int(m["matchday"]) for m in data.get("matches", [])
                             if m.get("matchday") is not None and int(m["matchday"]) > last_md})

        if not future_mds:
            await send_text_safe(update, context, "Nessuna giornata futura trovata.")
            return

        next_md = future_mds[0]

        first_kickoff = fetch_first_kickoff_for_md(next_md)
        if not first_kickoff:
            await send_text_safe(update, context, f"Giornata {next_md} trovata, ma nessun kickoff disponibile.")
            return

        notify_utc = first_kickoff - timedelta(minutes=30)

        kickoff_local = first_kickoff.astimezone(TZ_LOCAL).strftime("%A %d %B %Y, %H:%M")
        notify_local = notify_utc.astimezone(TZ_LOCAL).strftime("%A %d %B %Y, %H:%M")

        await send_text_safe(
    update,
    context,
    f" *Questo è lo stato di AngeloRanieriBot*\n\n"
    f" Ultima giornata notificata: *{last_md}*\n"
    f" Prossima giornata: *{next_md}*\n"
    f" Orario d'inizio della prima partita: *{kickoff_local}*\n"
    f" Angelo ti avviserà: *{notify_local}*\n"
)

    except Exception as e:
        await send_text_safe(update, context, f"Errore nel recupero status: {e}")


# chiamata una volta all'avvio per schedulare la prossima giornata
async def _post_init(app: Application) -> None:
    await schedule_next_round(app)

def main():
    if not TELEGRAM_TOKEN or not FOOTBALL_DATA_TOKEN or not GROUP_CHAT_ID:
        raise SystemExit("Config mancante: controlla TELEGRAM_TOKEN, FOOTBALL_DATA_TOKEN, GROUP_CHAT_ID nel .env")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("chatid", chatid))
    app.add_handler(CommandHandler("status", status))

    # check di backup giornaliero
    app.job_queue.run_repeating(check_and_schedule, interval=timedelta(days=1), first=timedelta(hours=6))

    # pianifica la prima volta non appena l'app parte
    app.post_init = _post_init

    app.run_polling()

if __name__ == "__main__":
    main()
