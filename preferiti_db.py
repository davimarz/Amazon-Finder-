import sqlite3
import time

def init_preferiti_db():
    with sqlite3.connect("preferiti.db") as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS preferiti (
                asin TEXT PRIMARY KEY,
                titolo TEXT,
                immagine_url TEXT,
                prezzo_iniziale REAL,
                prezzo_finale REAL,
                sconto TEXT,
                is_prime INTEGER,
                is_sped_gratis INTEGER,
                costo_spedizione REAL,
                voto_medio REAL,
                num_recensioni INTEGER,
                link_affiliato TEXT,
                data_salvataggio INTEGER DEFAULT 0
            )
        """)
        # Migrazione automatica se la colonna data_salvataggio non era presente
        c.execute("PRAGMA table_info(preferiti)")
        colonne = [info[1] for info in c.fetchall()]
        if "data_salvataggio" not in colonne:
            c.execute("ALTER TABLE preferiti ADD COLUMN data_salvataggio INTEGER DEFAULT 0")
        conn.commit()

def pulisci_preferiti_scaduti(ore=24):
    """Cancella tutti i preferiti salvati da più di N ore (default 24h = 86400s)."""
    init_preferiti_db()
    limite_tempo = int(time.time()) - (ore * 3600)
    with sqlite3.connect("preferiti.db") as conn:
        c = conn.cursor()
        c.execute("DELETE FROM preferiti WHERE data_salvataggio < ?", (limite_tempo,))
        conn.commit()

def ottieni_tutti_preferiti():
    # Rimuove in automatico i prodotti più vecchi di 24 ore prima della lettura
    pulisci_preferiti_scaduti(ore=24)
    with sqlite3.connect("preferiti.db") as conn:
        c = conn.cursor()
        c.execute("""
            SELECT asin, titolo, immagine_url, prezzo_iniziale, prezzo_finale, 
                   sconto, is_prime, is_sped_gratis, costo_spedizione, 
                   voto_medio, num_recensioni, link_affiliato, data_salvataggio 
            FROM preferiti
        """)
        rows = c.fetchall()
    
    preferiti = []
    for r in rows:
        preferiti.append({
            "asin": r[0],
            "titolo": r[1],
            "immagine_url": r[2],
            "prezzo_iniziale": r[3],
            "prezzo_finale": r[4],
            "sconto": r[5],
            "is_prime": bool(r[6]),
            "is_sped_gratis": bool(r[7]),
            "costo_spedizione": r[8],
            "voto_medio": r[9],
            "num_recensioni": r[10],
            "link_affiliato": r[11],
            "data_salvataggio": r[12]
        })
    return preferiti

def aggiungi_preferito(p):
    init_preferiti_db()
    timestamp_ora = int(time.time())
    with sqlite3.connect("preferiti.db") as conn:
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO preferiti 
            (asin, titolo, immagine_url, prezzo_iniziale, prezzo_finale, sconto, 
             is_prime, is_sped_gratis, costo_spedizione, voto_medio, num_recensioni, 
             link_affiliato, data_salvataggio)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p["asin"],
            p.get("titolo", ""),
            p.get("immagine_url", ""),
            p.get("prezzo_iniziale", 0.0),
            p.get("prezzo_finale", 0.0),
            p.get("sconto", ""),
            1 if p.get("is_prime") else 0,
            1 if p.get("is_sped_gratis") else 0,
            p.get("costo_spedizione", 0.0),
            p.get("voto_medio", 4.5),
            p.get("num_recensioni", 0),
            p.get("link_affiliato", ""),
            timestamp_ora
        ))
        conn.commit()

def rimuovi_preferito(asin):
    init_preferiti_db()
    with sqlite3.connect("preferiti.db") as conn:
        c = conn.cursor()
        c.execute("DELETE FROM preferiti WHERE asin = ?", (asin,))
        conn.commit()
