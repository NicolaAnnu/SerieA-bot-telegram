Ecco la **versione inglese completa** del tuo README ✅
Tradotta bene, fluida, corretta e in stile GitHub open-source 👇

---

````md
# Serie A Telegram Bot

A Telegram bot that sends a reminder **30 minutes before the first match of each Serie A matchday** — perfect for reminding fantasy football players to submit their lineup.

The bot runs fully automatically: once a matchday ends, it schedules the next reminder on its own.

This project is under active development: new features and improvements will be added regularly.

---

## 🚀 Features

- Reminder 30 minutes before the first match of each matchday
- Automatic scheduling across the full Serie A season
- Works in Telegram groups
- `/status` command to check the next notification
- Railway deployment for 24/7 uptime

---

## 🧰 Requirements

- Python 3.9+
- Telegram Bot Token (`@BotFather`)
- football-data.org API key (FREE tier available)
- Railway account for cloud hosting

---

## 💻 Local Installation

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

## ☁️ Deployment on Railway

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

4. Deploy 🎉

---

## 📁 Main Files

| File               | Purpose                         |
| ------------------ | ------------------------------- |
| `main.py`          | Main bot logic                  |
| `requirements.txt` | Python dependencies             |
| `Procfile`         | Railway start configuration     |
| `getid.py`         | Chat ID helper (local use only) |

---

## ⚙️ How it Works

* Fetches the next Serie A matchday
* Detects the first match kickoff
* Schedules a reminder 30 minutes earlier
* After sending, automatically prepares the next matchday

---

##  Bot Commands

| Command   | Description                             |
| --------- | --------------------------------------- |
| `/start`  | Welcome message                         |
| `/status` | Shows the next scheduled notification   |
| `/chatid` | Retrieves chat ID (local helper script not shareable) |

---

##  Contributing

Contributions are welcome!
Feel free to open an **issue** or submit a **pull request**.

---

## 📬 Contact

Telegram: `@yourUsername`

---

##  Enjoy your fantasy football — and Forza Serie A! 🇮🇹