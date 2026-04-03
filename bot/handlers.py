import re
from datetime import datetime, timedelta
import requests
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from .state import load_state
from .constants import giorni, mesi
from .config import FOOTBALL_DATA_TOKEN, GROUP_CHAT_ID, TZ_LOCAL, logger
from .api import fetch_standings_SA, _fmt_row, formatta_it, fetch_fixtures_for_md, fetch_first_kickoff_for_md


async def classifica_handler(update, context):
    try:
        table = fetch_standings_SA()
        if not table:
            await send_text_safe(update, context, "Classifica non disponibile al momento.")
            return

        header = (
    "```\n"
    "Pos  Squadra              Pt   G   V   N   P\n"
    "--------------------------------------------\n"
    "```"
)


        rows = [ _fmt_row(row) for row in table ]
        body = "```\n" + "\n".join(rows) + "\n```"

        msg = "*Classifica Serie A*\n" + header + body
        await send_text_safe(update, context, msg)

    except requests.HTTPError as e:
        await send_text_safe(update, context, f"Errore API classifica: {e}")
        logger.exception("HTTPError classifica: %s", e)
    except Exception as e:
        await send_text_safe(update, context, f"Errore nel recupero classifica: {e}")
        logger.exception("Errore classifica: %s", e)

async def partite_handler(update, context):
    try:
        text = (update.message.text or "").strip()

        m = re.match(r"^/partite(\d{1,2})\b", text)
        if m:
            md = int(m.group(1))
        else:
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

        # lista
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
   await send_text_safe(
    update, 
    context, 
    "Ciao! Pianificherò un promemoria un'ora' prima della prossima giornata di Serie A. "
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

        notify_utc = first_kickoff - timedelta(minutes=60)
        notify_utc1day = first_kickoff - timedelta(hours=24)

        # kickoff locale
        dt_k = first_kickoff.astimezone(TZ_LOCAL)
        day_k = giorni[dt_k.strftime("%A")]
        month_k = mesi[dt_k.strftime("%B")]
        kickoff_local = f"{day_k} {dt_k.strftime('%d')} {month_k} {dt_k.strftime('%Y, %H:%M')}"

        # notifica locale
        dt_y = notify_utc1day.astimezone(TZ_LOCAL)
        dt_n = notify_utc.astimezone(TZ_LOCAL)
        day_n = giorni[dt_n.strftime("%A")]
        day_y = giorni[dt_y.strftime("%A")]
        month_n = mesi[dt_n.strftime("%B")]
        month_y = mesi[dt_y.strftime("%B")]
        notify_local = f"{day_n} {dt_n.strftime('%d')} {month_n} {dt_n.strftime('%Y, %H:%M')}"
        notify_local1day = f"{day_y} {dt_y.strftime('%d')} {month_y} {dt_y.strftime('%Y, %H:%M')}"


        await send_text_safe(
    update,
    context,
    f" *Questo è lo stato di AngeloRanieriBot*\n\n"
    f" Ultima giornata notificata: *{last_md}*\n"
    f" Prossima giornata: *{next_md}*\n"
    f" Orario d'inizio della prima partita: *{kickoff_local}*\n"
    f" Angelo ti avviserà sia: Un giorno prima: *{notify_local1day}* e sia un'ora prima: *{notify_local}*\n"
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