import sqlite3

DB_NAME = "preferiti.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preferiti (
                asin TEXT PRIMARY KEY,
                titolo TEXT,
                prezzo_finale REAL,
                prezzo_iniziale REAL,
                sconto TEXT,
                info_spedizione TEXT,
                costo_spedizione REAL,
                immagine_url TEXT,
                link_affiliato TEXT,
                data_aggiunta TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def ottieni_tutti_preferiti():
    init_db()
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM preferiti ORDER BY data_aggiunta DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def aggiungi_preferito(p):
    init_db()
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO preferiti (
                asin, titolo, prezzo_finale, prezzo_iniziale, sconto, 
                info_spedizione, costo_spedizione, immagine_url, link_affiliato
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p["asin"], p["titolo"], p.get("prezzo_finale", 0.0), p.get("prezzo_iniziale", 0.0),
            p.get("sconto", ""), p.get("info_spedizione", ""), p.get("costo_spedizione", 0.0),
            p.get("immagine_url", ""), p.get("link_affiliato", "")
        ))
        conn.commit()

def rimuovi_preferito(asin):
    init_db()
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM preferiti WHERE asin = ?", (asin,))
        conn.commit()