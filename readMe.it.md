# Serie A Telegram Bot

Un bot Telegram pensato per gli appassionati di Serie A e Fantacalcio.
Invia automaticamente un promemoria 30 minuti prima della prima partita di ogni giornata di Serie A, così nessuno dimentica di inserire la formazione in tempo.

Il bot funziona in totale autonomia: una volta terminata una giornata, riconosce quella successiva e programma da solo il prossimo avviso, senza bisogno di interventi manuali.
Oltre ai promemoria, mette a disposizione diversi comandi utili per consultare rapidamente informazioni sulla stagione: è possibile controllare lo stato del bot e la prossima notifica, visualizzare la classifica aggiornata della Serie A, e ottenere il calendario delle partite di qualsiasi giornata semplicemente digitando /partiteX (ad esempio /partite10 per vedere le partite della 10ª giornata).
In aggiunta, il comando /comandi consente di visualizzare rapidamente tutte le funzionalità disponibili.

Il progetto è in costante aggiornamento: nuove funzioni e miglioramenti verranno aggiunti regolarmente per rendere il bot sempre più completo e utile.

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
| `/classifica` | Mostra la classifica attuale di Serie A           |
| `/partiteX` | Mostra le partite della giornata X           |
| `/comandi` | Mostra i comandi disponibili           |

---

##  Contributi

Contributi e miglioramenti sono benvenuti!
Apri una **issue** o una **pull request**.



#  Buon fantacalcio e forza Serie A!
