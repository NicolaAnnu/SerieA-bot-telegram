# Serie A Telegram Bot

Un bot Telegram pensato per gli appassionati di Serie A e Fantacalcio. Invia automaticamente due promemoria prima della prima partita di ogni giornata di Serie A: uno 24 ore prima e uno 60 minuti prima del calcio d'inizio, cosi nessuno dimentica di inserire la formazione in tempo.

Il bot funziona in totale autonomia: una volta terminata una giornata, riconosce quella successiva e programma da solo i prossimi avvisi, senza bisogno di interventi manuali. Oltre ai promemoria, mette a disposizione diversi comandi utili per consultare rapidamente informazioni sulla stagione: puoi controllare lo stato del bot e la prossima notifica, visualizzare la classifica aggiornata della Serie A, e ottenere il calendario delle partite di qualsiasi giornata semplicemente digitando /partiteX (ad esempio /partite10 per vedere le partite della 10a giornata). In aggiunta, il comando /comandi consente di visualizzare rapidamente tutte le funzionalita disponibili.

Il progetto e in costante aggiornamento: nuove funzioni e miglioramenti verranno aggiunti regolarmente per rendere il bot sempre piu completo e utile.

---

## Funzionalita

- Doppio promemoria: 24 ore e 60 minuti prima del primo match della giornata
- Aggiornamento automatico giornata dopo giornata
- Supporto gruppi Telegram
- Comando `/status` per vedere la programmazione
- Deploy su Railway per funzionamento H24

---

## Requisiti

- Python 3.9+
- Token Telegram Bot (`@BotFather`)
- API Key football-data.org (FREE)
- Railway (per esecuzione continua)

---

## Installazione Locale

```bash
git clone https://github.com/<tuo-username>/SerieA-bot-telegram.git
cd SerieA-bot-telegram
pip install -r requirements.txt
```

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

## Deploy su Railway

1. Collega la repo a Railway
2. Imposta start command:

```
python -u main.py
```

3. Aggiungi variabili in Railway -> Variables:

| Variabile           | Descrizione           |
| ------------------- | --------------------- |
| TELEGRAM_TOKEN      | Token bot Telegram    |
| FOOTBALL_DATA_TOKEN | API key football-data |
| GROUP_CHAT_ID       | ID gruppo Telegram    |

4. Deploy

---

## File principali

| File               | Funzione                       |
| ------------------ | ------------------------------ |
| `main.py`          | Codice bot                     |
| `requirements.txt` | Dipendenze                     |
| `Procfile`         | Config Railway                 |
| `getid.py`         | Recupero Chat ID (solo locale) |

---

## Funzionamento

* Trova la prima partita della prossima giornata
* Pianifica due notifiche (24 ore e 60 minuti prima del calcio d'inizio)
* Dopo l'invio, passa alla giornata successiva automaticamente

---

## Comandi Bot

| Comando       | Descrizione                                               |
| ------------- | --------------------------------------------------------- |
| `/start`      | Messaggio di benvenuto                                   |
| `/status`     | Mostra prossima notifica                                  |
| `/chatid`     | Recupera Chat ID (script separato non condivisibile)      |
| `/classifica` | Mostra la classifica attuale di Serie A                   |
| `/partiteX`   | Mostra le partite della giornata X                        |
| `/comandi`    | Mostra i comandi disponibili                              |

---

## Contributi

Contributi e miglioramenti sono benvenuti! Apri una issue o una pull request.

# Buon fantacalcio e forza Serie A!