import logging
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes
import os, json
from typing import Optional
from telegram.ext import MessageHandler, CommandHandler, filters
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
# Dizionari per la traduzione di giorni e mesi in italiano
giorni = {
    "Monday": "Lunedì",
    "Tuesday": "Martedì",
    "Wednesday": "Mercoledì",
    "Thursday": "Giovedì",
    "Friday": "Venerdì",
    "Saturday": "Sabato",
    "Sunday": "Domenica"
}

mesi = {
    "January": "Gennaio",
    "February": "Febbraio",
    "March": "Marzo",
    "April": "Aprile",
    "May": "Maggio",
    "June": "Giugno",
    "July": "Luglio",
    "August": "Agosto",
    "September": "Settembre",
    "October": "Ottobre",
    "November": "Novembre",
    "December": "Dicembre"
}

# ----------------- Config -----------------
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
FOOTBALL_DATA_TOKEN = os.getenv("FOOTBALL_DATA_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID", "0"))

# Europe/Rome per orari umani
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

def fetch_standings_SA():
    """
    Ritorna la classifica totale (home+away) della Serie A come lista di dict.
    Usa football-data.org v4 (piano free: League Tables incluso).
    """
    url = "https://api.football-data.org/v4/competitions/SA/standings"
    headers = {"X-Auth-Token": FOOTBALL_DATA_TOKEN}
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    data = r.json()

    # Trova la standing 'TOTAL' (classifica complessiva)
    standings = data.get("standings", [])
    total = next((s for s in standings if s.get("type") == "TOTAL"), None)
    if not total:
        return []

    return total.get("table", [])  # lista di team rows


def _fmt_row(row, name_width=18):
    """
    Formatta una riga tabellare monospace:
    Pos  Squadra               Pt  G  V  N  P  GF:GS  DR
    """
    pos = row.get("position", 0)
    team = (row.get("team", {}) or {}).get("shortName") or (row.get("team", {}) or {}).get("name", "—")
    played = row.get("playedGames", 0)
    won = row.get("won", 0)
    draw = row.get("draw", 0)
    lost = row.get("lost", 0)
    pts = row.get("points", 0)
    gf = row.get("goalsFor", 0)
    ga = row.get("goalsAgainst", 0)
    gd = row.get("goalDifference", 0)

    # taglia/padding nome squadra per allineamento
    team = (team[:name_width]).ljust(name_width)
    # DR con segno
    gd_str = f"{gd:+d}"

    return f"{pos:>2}  {team}  {pts:>3} {played:>3} {won:>3} {draw:>3} {lost:>3}  {gf:>2}:{ga:<2}  {gd_str:>3}"

def formatta_it(dt):
    dt = dt.astimezone(TZ_LOCAL)
    g = giorni[dt.strftime("%A")]
    m = mesi[dt.strftime("%B")]
    return f"{g} {dt.strftime('%d')} {m} {dt.strftime('%Y, %H:%M')}"

# --- fetch calendario giornata ---
def fetch_fixtures_for_md(md: int):
    url = "https://api.football-data.org/v4/competitions/SA/matches"
    headers = {"X-Auth-Token": FOOTBALL_DATA_TOKEN}
    params = {"matchday": md}  # tutte le partite della giornata
    r = requests.get(url, headers=headers, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    matches = data.get("matches", [])
    # ordina per kickoff
    matches.sort(key=lambda m: m.get("utcDate") or "")
    return matches


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
            
            dt_k = first_kickoff.astimezone(TZ_LOCAL)
            day_k = giorni[dt_k.strftime("%A")]
            month_k = mesi[dt_k.strftime("%B")]
            local_kick = f"{day_k} {dt_k.strftime('%d')} {month_k} {dt_k.strftime('%Y, %H:%M')}"

            dt_n = notify_utc.astimezone(TZ_LOCAL)
            day_n = giorni[dt_n.strftime("%A")]
            month_n = mesi[dt_n.strftime("%B")]
            local_notify = f"{day_n} {dt_n.strftime('%d')} {month_n} {dt_n.strftime('%Y, %H:%M')}"

            logger.info( "Pianificata NOTIFICA (una sola) per MD%s alle %s (local). Primo kickoff: %s (local).",
                        md, local_notify, local_kick
)


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

async def classifica_handler(update, context):
    try:
        table = fetch_standings_SA()
        if not table:
            await send_text_safe(update, context, "Classifica non disponibile al momento.")
            return

        # Intestazione + righe
        header = (
            "```\n"
            "Pos  Squadra              Pt   G   V   N   P   GF:GS  DR\n"
            "--------------------------------------------------------\n"
            "```"
        )

        rows = [ _fmt_row(row) for row in table ]
        body = "```\n" + "\n".join(rows) + "\n```"

        msg = "*Classifica Serie A*\n" + header + body
        await send_text_safe(update, context, msg)

    except requests.HTTPError as e:
        # gestione rate-limit 429 o altri errori HTTP dell'API
        await send_text_safe(update, context, f"Errore API classifica: {e}")
        logger.exception("HTTPError classifica: %s", e)
    except Exception as e:
        await send_text_safe(update, context, f"Errore nel recupero classifica: {e}")
        logger.exception("Errore classifica: %s", e)

async def partite_handler(update, context):
    try:
        text = (update.message.text or "").strip()

        # 1) /partite10 (senza spazio)
        m = re.match(r"^/partite(\d{1,2})\b", text)
        if m:
            md = int(m.group(1))
        else:
            # 2) /partite 10 (con argomento)
            if context.args and len(context.args) >= 1 and context.args[0].isdigit():
                md = int(context.args[0])
            else:
                await send_text_safe(update, context, "Uso: `/partite10` oppure `/partite 10`")
                return

        if not (1 <= md <= 38):
            await send_text_safe(update, context, "La giornata deve essere tra 1 e 38.")
            return

        matches = fetch_fixtures_for_md(md)
        if not matches:
            await send_text_safe(update, context, f"Nessuna partita trovata per la giornata {md}.")
            return

        # costruisci lista
        righe = [f"*Calendario Serie A — Giornata {md}*"]
        for match in matches:
            utc = match.get("utcDate")
            if not utc:
                continue
            dt_utc = datetime.fromisoformat(utc.replace("Z", "+00:00"))
            when = formatta_it(dt_utc)
            home = match.get("homeTeam", {}).get("shortName") or match.get("homeTeam", {}).get("name", "Casa")
            away = match.get("awayTeam", {}).get("shortName") or match.get("awayTeam", {}).get("name", "Trasferta")
            righe.append(f"• {when} — *{home}* vs *{away}*")

        msg = "\n".join(righe)
        await send_text_safe(update, context, msg)

    except Exception as e:
        logger.exception("Errore partite_handler: %s", e)
        await send_text_safe(update, context, f"Errore nel recupero calendario: {e}")

async def send_lineups_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    data = context.job.data or {}
    md = int(data.get("matchday"))
    kickoff_utc = data.get("kickoff_utc")

    kickoff_local = kickoff_utc.astimezone(TZ_LOCAL).strftime("%d/%m %H:%M")
    text = (
        f"Salve sono Angelo Ranieri il bot, sono qui per ricordarvi che\n"
        f"bisogna pubblicare la FORMAZIONE!!\n"
        f"Tra 30 minuti inizia la *Giornata {md}* di Serie A "
        f"(primo calcio d'inizio: *{kickoff_local}*).\n\n"
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
   await send_text_safe(
    update, 
    context, 
    "Ciao! Pianificherò un promemoria 30' prima della prossima giornata di Serie A. "
    "Usa /status per i dettagli."
)
async def partitedefault(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_text_safe(
    update, 
    context, 
    "Devi utilizzare il comando /partite seguito dal numero della giornata per poter visualizzare il calendario delle partite."
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

# kickoff locale
        dt_k = first_kickoff.astimezone(TZ_LOCAL)
        day_k = giorni[dt_k.strftime("%A")]
        month_k = mesi[dt_k.strftime("%B")]
        kickoff_local = f"{day_k} {dt_k.strftime('%d')} {month_k} {dt_k.strftime('%Y, %H:%M')}"

# notifica locale
        dt_n = notify_utc.astimezone(TZ_LOCAL)
        day_n = giorni[dt_n.strftime("%A")]
        month_n = mesi[dt_n.strftime("%B")]
        notify_local = f"{day_n} {dt_n.strftime('%d')} {month_n} {dt_n.strftime('%Y, %H:%M')}"


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

async def comandi(update, context):
    text = (
        "*Lista comandi disponibili*\n\n"
        "*Angelo Ranieri Bot*\n"
        "• `/start` — Messaggio di benvenuto\n"
        "• `/status` — Stato bot e prossima notifica\n"
        "• `/comandi` — Elenco comandi\n\n"
        " *Calendario partite*\n"
        "• `/partiteX` — Mostra le partite della giornata X\n"
        "_(puoi usare qualsiasi giornata: /partite9, /partite15 ecc.)_\n\n"
        "*Classifica Serie A*\n"
        "• `/classifica` — Classifica aggiornata Serie A\n\n"
        "Presto lo sviluppatore aggiungerà altre nuove funzionalità! Io sono ANGELO RANIERI BOT!"
    )

    await send_text_safe(update, context, text)

# chiamata una volta all'avvio per schedulare la prossima giornata
async def _post_init(app: Application) -> None:
    await schedule_next_round(app)

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

if __name__ == "__main__":
    main()
