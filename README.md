# Scala dei Turchi - Amazon Affiliate Streamlit v2

## Modifiche richieste
- Scheda Contatti nascosta dalla navigazione pubblica; il codice è mantenuto.
- Vetrina ricaricata all'avvio di una nuova sessione/browser refresh.
- Click su Vetrina forza una nuova richiesta SearchItems.
- Ordinamento predefinito: Prezzo minimo.
- Rimossi Rilevanza e Popolarità dalla UI.
- Aggiunto "Quantità vendite".
- "Quantità vendite" usa `browseNodeInfo.websiteSalesRank` (Best Sellers Rank)
  perché Amazon non espone il numero esatto di unità vendute.
- Ripristinata la palette grafica del vecchio sito:
  azzurro/blu, verde, arancione, sfondo sfumato e badge `AI DEALS`.
- Restano eliminati scraping HTML, recensioni inventate e spedizioni inventate.

## Flusso dati
SearchItems -> ASIN -> GetItems -> OffersV2 Buy Box
                              -> WebsiteSalesRank

## Deploy
Carica su GitHub:
- app.py
- amazon_api.py
- requirements.txt
- .gitignore

Inserisci le credenziali reali solo nei Secrets di Streamlit Cloud.

## Nota "Quantità vendite"
Non è un conteggio di pezzi venduti.
Il valore ufficiale disponibile è il Best Sellers Rank Amazon:
un numero più basso indica un posizionamento vendite migliore.


## Fix V3 - nessun prodotto in Vetrina/Cerca

Correzioni:
- `GetItems` legge `itemResults` (nome corrente nella Creators API).
- compatibilità difensiva anche con `itemsResult`.
- rimossa la resource non ammessa `offersV2.listings.violatesMAP`.
- SearchItems conserva titolo, immagine e detailPageURL.
- se un singolo GetItems fallisce, la scheda resta visibile senza prezzo inventato.
- aggiunta diagnostica HTTP priva di secrets.
- pulsante Cerca forzato azzurro; hover verde.


## V4 - fallback per account Creators API temporaneamente non idoneo

- Niente errore HTTP tecnico mostrato all'utente.
- Vetrina con categorie Amazon affiliate quando le schede automatiche non sono disponibili.
- Ricerca con pulsante diretto alla keyword su Amazon.it.
- Link con Partner Tag dai Secrets.
- Nessun prezzo, prodotto, recensione o vendita inventati.
- Dopo il primo 403 della sessione l'app evita chiamate ripetute.
- In una nuova sessione l'app riprova automaticamente Creators API.
