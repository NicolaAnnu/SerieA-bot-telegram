# Serie A Telegram Bot

Bot Telegram che invia un promemoria **30 minuti prima della prima partita di ogni giornata di Serie A**, utile per ricordare ai partecipanti del fantacalcio di pubblicare la formazione.

Il bot funziona in automatico: appena finisce una giornata, pianifica da solo il prossimo avviso

Questo progetto è in sviluppo attivo: nuove funzionalità e miglioramenti verranno aggiunti

---

##  Funzionalità

- Promemoria 30' prima del primo match della giornata
- Aggiornamento automatico giornata dopo giornata
- Supporto gruppi Telegram
- Comando `/status` per vedere la programmazione
- Deploy su Railway per funzionamento H24

---

##  Requisiti

- Python 3.9+
- Token Telegram Bot (`@BotFather`)
- API Key football-data.org (FREE)
- Railway (per esecuzione continua)

---

##  Installazione Locale

```bash
git clone https://github.com/<tuo-username>/SerieA-bot-telegram.git
cd SerieA-bot-telegram
pip install -r requirements.txt
````

Crea `.env`:

```
TELEGRAM_TOKEN=xxxxx
FOOTBALL_DATA_TOKEN=xxxxx
GROUP_CHAT_ID=-100xxxxxxxx
```

Esegui il bot:

```bash
python main.py
```

---

##  Deploy su Railway

1. Collega la repo a Railway
2. Imposta start command:

```
python -u main.py
```

3. Aggiungi Variabili in **Railway → Variables**:

| Variabile           | Descrizione           |
| ------------------- | --------------------- |
| TELEGRAM_TOKEN      | Token bot Telegram    |
| FOOTBALL_DATA_TOKEN | API key football-data |
| GROUP_CHAT_ID       | ID gruppo Telegram    |

4. Deploy 

---

##  File principali

| File               | Funzione                       |
| ------------------ | ------------------------------ |
| `main.py`          | Codice bot                     |
| `requirements.txt` | Dipendenze                     |
| `Procfile`         | Config Railway                 |
| `getid.py`         | Recupero Chat ID (solo locale) |

---

##  Funzionamento

* Trova la prima partita della prossima giornata
* Pianifica la notifica 30 minuti prima
* Dopo l'invio, passa alla giornata successiva automaticamente

---

##  Comandi Bot

| Comando   | Descrizione                        |
| --------- | ---------------------------------- |
| `/start`  | Messaggio di benvenuto             |
| `/status` | Mostra prossima notifica           |
| `/chatid` | Recupera Chat ID (script separato non condivisibile) |

---

##  Contributi

Contributi e miglioramenti sono benvenuti!
Apri una **issue** o una **pull request**.



#  Buon fantacalcio e forza Serie A!
