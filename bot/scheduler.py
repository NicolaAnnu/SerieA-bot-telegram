from datetime import datetime, timedelta, timezone
import requests
from telegram.constants import ParseMode
from telegram.ext import Application, ContextTypes

from .state import load_state, save_state
from .constants import giorni, mesi
from .config import FOOTBALL_DATA_TOKEN, GROUP_CHAT_ID, TZ_LOCAL, logger
from .api import fetch_first_kickoff_for_md


async def schedule_next_round(app: Application) -> None:
    """
    Notifica UNA SOLA VOLTA per giornata:
    - Trova la prossima giornata con MD > last_notified_matchday.
    - Calcola il PRIMO calcio d'inizio di quella giornata (anche se alcune partite sono già finite).
    - Se la finestra 60' prima è già passata (o la partita è iniziata), marca la giornata e passa oltre.
    - Altrimenti pianifica la notifica esattamente a T-60'.
    """

    try:
        state = load_state()
        last_md = int(state.get("last_notified_matchday", 0))
        now_utc = datetime.now(timezone.utc)

        url = "https://api.football-data.org/v4/competitions/SA/matches"
        headers = {"X-Auth-Token": FOOTBALL_DATA_TOKEN}
        params = {"status": "SCHEDULED"}
        r = requests.get(url, headers=headers, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()

        future_mds = sorted({
            int(m["matchday"]) for m in data.get("matches", [])
            if m.get("matchday") is not None and 1 <= int(m["matchday"]) <= 38
        })
        future_mds = [md for md in future_mds if md > last_md]

        if not future_mds:
            logger.info(
                "Nessuna giornata futura oltre MD%s. Riprovo tra 1 giorno.",
                last_md
            )
            app.job_queue.run_once(check_and_schedule, when=timedelta(days=1))
            return

        planned = False
        for md in future_mds:
            first_kickoff = fetch_first_kickoff_for_md(md)
            if not first_kickoff:
                logger.info("MD%s non ha partite (API). Continuo con la successiva.", md)
                continue

            notify_utc1day = first_kickoff - timedelta(days=1)       # 24 ore prima
            notify_utc = first_kickoff - timedelta(minutes=60)       # 1 ora prima

            # Se il primo kickoff è già iniziato → salta
            if now_utc >= first_kickoff:
                logger.info(
                    "MD%s: primo kickoff %s già iniziato. Marco come notificata e passo oltre.",
                    md,
                    first_kickoff.isoformat(),
                )
                state["last_notified_matchday"] = md
                save_state(state)
                continue

            # Se la finestra T-60' è passata → salta
            if now_utc >= notify_utc:
                logger.info(
                    "MD%s: finestra T-60' (%s) già passata. Salto giornata e passo oltre.",
                    md,
                    notify_utc.isoformat(),
                )
                state["last_notified_matchday"] = md
                save_state(state)
                continue

            # 3) Pulisci job precedenti
            for job in app.job_queue.get_jobs_by_name("md_notify"):
                job.schedule_removal()

            for job in app.job_queue.get_jobs_by_name("md_notify_24h"):
                job.schedule_removal()

            # 4) Notifica 1 ora prima
            app.job_queue.run_once(
                send_lineups_reminder,
                when=notify_utc,
                name="md_notify",
                data={"matchday": md, "kickoff_utc": first_kickoff},
            )

            # 5) Notifica 24h prima (solo se ancora futura)
            if now_utc < notify_utc1day:
                app.job_queue.run_once(
                    send_lineups_reminder_24h,
                    when=notify_utc1day,
                    name="md_notify_24h",
                    data={"matchday": md, "kickoff_utc": first_kickoff},
                )

                dt_k = first_kickoff.astimezone(TZ_LOCAL)
                day_k = giorni[dt_k.strftime("%A")]
                month_k = mesi[dt_k.strftime("%B")]
                local_kick = (
                    f"{day_k} {dt_k.strftime('%d')} {month_k} "
                    f"{dt_k.strftime('%Y, %H:%M')}"
                )

                dt_n = notify_utc.astimezone(TZ_LOCAL)
                day_n = giorni[dt_n.strftime("%A")]
                month_n = mesi[dt_n.strftime("%B")]
                local_notify = (
                    f"{day_n} {dt_n.strftime('%d')} {month_n} "
                    f"{dt_n.strftime('%Y, %H:%M')}"
                )

                logger.info(
                    "Pianificata NOTIFICA (una sola) per MD%s alle %s (local). "
                    "Primo kickoff: %s (local).",
                    md, local_notify, local_kick
                )

                planned = True
                break

        if not planned:
            logger.info(
                "Nessuna MD pianificabile (finestra già passata). Nuovo check tra 2 ore."
            )
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
        f"Tra un'ora inizia la *Giornata {md}* di Serie A "
        f"(primo calcio d'inizio: *{kickoff_local}*).\n\n"
        f"Pubblicate la formazione ora! @NickNapoli22 "
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

    # Pianifica la prossima giornata
    await schedule_next_round(context.application)


async def send_lineups_reminder_24h(context: ContextTypes.DEFAULT_TYPE) -> None:
    data = context.job.data or {}
    md = int(data.get("matchday"))
    kickoff_utc = data.get("kickoff_utc")

    # Orario del primo kickoff in timezone locale
    kickoff_local = kickoff_utc.astimezone(TZ_LOCAL).strftime("%d/%m %H:%M")

    text = (
        f"Salve sono Angelo Ranieri il bot, sono qui per ricordarvi che\n"
        f"domani inizia la *Giornata {md}* di Serie A "
        f"(primo calcio d'inizio: *{kickoff_local}*).\n\n"
        f"Preparate e pubblicate la FORMAZIONE entro domani! @NickNapoli22 "
    )

    try:
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
        logger.info(f"Messaggio 24h prima inviato per MD{md}.")
    except Exception as e:
        logger.exception("Errore nell'invio del messaggio 24h prima: %s", e)


# chiamata una volta all'avvio per schedulare la prossima giornata
async def _post_init(app: Application) -> None:
    await schedule_next_round(app)