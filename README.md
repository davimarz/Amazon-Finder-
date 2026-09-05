# Amazon Affiliate Streamlit - versione ottimizzata

## File
- `app.py`: UI, ricerca, paginazione, contatti e privacy.
- `amazon_api.py`: integrazione Amazon Creators API.
- `requirements.txt`: dipendenze minime.
- `.gitignore`: impedisce di pubblicare secrets e file locali.
- `.streamlit/secrets.example.toml`: schema di configurazione senza credenziali reali.

## Modifiche principali
1. Eliminato lo scraping HTML Amazon come fonte dati.
2. Eliminati `beautifulsoup4` e `curl_cffi`.
3. `SearchItems` trova gli ASIN; `GetItems` verifica i dettagli in batch da 10.
4. Prezzo mostrato solo dalla Buy Box verificata via `OffersV2`.
5. Nessuna recensione, vendita o spedizione inventata.
6. Nessun Partner Tag hardcoded nel codice.
7. Retry controllato su 429/5xx e refresh token su 401.
8. Cache separata: risultati ricerca 10 minuti, prezzi 2 minuti.
9. Ricerca progressiva 10 -> 20 -> 30 -> 40 -> 50.
10. Rimosso SQLite locale per il rate-limit del form contatti.
11. Errori SMTP non esposti integralmente all'utente.
12. Dipendenze con range di versione per ridurre rotture improvvise.

## Streamlit Cloud
Imposta i Secrets dal pannello dell'app, non nel repository GitHub.

Esempio:

```toml
[amazon_api]
partner_tag = "..."
client_id = "..."
client_secret = "..."

[email]
sender = "..."
app_password = "..."
recipient = "..."
```

Dopo il commit dei file, esegui un Reboot dell'app.

## Nota sui prezzi
Amazon può mostrare a un cliente specifico un prezzo diverso per account,
indirizzo di consegna, coupon o promozioni. Il sito usa la Buy Box disponibile
tramite Creators API e non tenta di ricavare prezzi dal markup HTML.
