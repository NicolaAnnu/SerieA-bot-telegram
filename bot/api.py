import requests
from datetime import datetime
from typing import Optional

from .config import FOOTBALL_DATA_TOKEN, TZ_LOCAL
from .constants import giorni, mesi


# ----------------- API Serie A -----------------
def fetch_first_kickoff_for_md(md: int) -> Optional[datetime]:
    """
    Ritorna il PRIMO kickoff (UTC, aware) della giornata md (1..38), considerando TUTTE le partite
    di quella giornata (FINISHED/IN_PLAY/TIMED/SCHEDULED). Se non trova partite, None.
    """
    url = "https://api.football-data.org/v4/competitions/SA/matches"
    headers = {"X-Auth-Token": FOOTBALL_DATA_TOKEN}
    params = {"matchday": md}
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
    
    standings = data.get("standings", [])
    total = next((s for s in standings if s.get("type") == "TOTAL"), None)
    if not total:
        return []

    return total.get("table", [])

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

    team = (team[:name_width]).ljust(name_width)

    return f"{pos:>2}  {team}  {pts:>3} {played:>3} {won:>3} {draw:>3} {lost:>3}"

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