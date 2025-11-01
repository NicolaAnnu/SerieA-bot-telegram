# Serie A Telegram Bot

A Telegram bot designed for Serie A and Fantacalcio enthusiasts.
It automatically sends a reminder 30 minutes before the first match of every Serie A matchday, ensuring that participants remember to submit their lineup on time.

The bot operates completely autonomously: once a matchday ends, it identifies the next one and schedules the upcoming reminder without any manual action.
In addition to notifications, the bot now offers useful interactive commands, allowing users to check the status of the next matchday and reminder time, view the full Serie A standings, and request the match schedule of any gameweek simply by typing /partiteX (for example, /partite10 to see matchday 10 fixtures).
A dedicated /comandi menu is also available, displaying all supported commands in a convenient format.

This project is actively maintained and continuously evolving, with new features and improvements being introduced on a regular basis.

---

##  Features

- Reminder 30 minutes before the first match of each matchday
- Automatic scheduling across the full Serie A season
- Works in Telegram groups
- `/status` command to check the next notification
- Railway deployment for 24/7 uptime

---

##  Requirements

- Python 3.9+
- Telegram Bot Token (`@BotFather`)
- football-data.org API key (FREE tier available)
- Railway account for cloud hosting

---

##  Local Installation

```bash
git clone https://github.com/<your-username>/SerieA-bot-telegram.git
cd SerieA-bot-telegram
pip install -r requirements.txt
````

Create a `.env` file:

```
TELEGRAM_TOKEN=xxxxx
FOOTBALL_DATA_TOKEN=xxxxx
GROUP_CHAT_ID=-100xxxxxxxx
```

Run the bot:

```bash
python main.py
```

---

##  Deployment on Railway

1. Connect your GitHub repository to Railway
2. Set the start command:

```
python -u main.py
```

3. Add environment variables in **Railway → Variables**:

| Variable            | Description            |
| ------------------- | ---------------------- |
| TELEGRAM_TOKEN      | Telegram bot token     |
| FOOTBALL_DATA_TOKEN | Football-data API key  |
| GROUP_CHAT_ID       | Telegram group chat ID |

4. Deploy 

---

##  Main Files

| File               | Purpose                         |
| ------------------ | ------------------------------- |
| `main.py`          | Main bot logic                  |
| `requirements.txt` | Python dependencies             |
| `Procfile`         | Railway start configuration     |
| `getid.py`         | Chat ID helper (local use only) |

---

##  How it Works

* Fetches the next Serie A matchday
* Detects the first match kickoff
* Schedules a reminder 30 minutes earlier
* After sending, automatically prepares the next matchday

---

##  Bot Commands

## Bot Commands

| Command       | Description                                      |
| ------------- | ------------------------------------------------ |
| `/start`      | Welcome message                                  |
| `/status`     | Shows the next scheduled notification            |
| `/chatid`     | Retrieves Chat ID (separate non-shareable script)|
| `/classifica` | Displays the current Serie A standings           |
| `/partiteX`   | Shows the matches for matchday X                 |
| `/comandi`    | Shows available commands                         |


---

##  Contributing

Contributions are welcome!
Feel free to open an **issue** or submit a **pull request**.




# Enjoy your fantasy football — and Forza Serie A! 🇮🇹