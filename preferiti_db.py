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
                is_prime INTEGER DEFAULT 0,
                immagine_url TEXT,
                link_affiliato TEXT,
                voto_medio REAL DEFAULT 4.5,
                num_recensioni INTEGER DEFAULT 100,
                data_aggiunta TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("PRAGMA table_info(preferiti)")
        colonne = [row[1] for row in cursor.fetchall()]
        if "is_prime" not in colonne:
            cursor.execute("ALTER TABLE preferiti ADD COLUMN is_prime INTEGER DEFAULT 0")
        if "voto_medio" not in colonne:
            cursor.execute("ALTER TABLE preferiti ADD COLUMN voto_medio REAL DEFAULT 4.5")
        if "num_recensioni" not in colonne:
            cursor.execute("ALTER TABLE preferiti ADD COLUMN num_recensioni INTEGER DEFAULT 100")
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
                info_spedizione, costo_spedizione, is_prime, immagine_url, link_affiliato,
                voto_medio, num_recensioni
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p["asin"], p["titolo"], p.get("prezzo_finale", 0.0), p.get("prezzo_iniziale", 0.0),
            p.get("sconto", ""), p.get("info_spedizione", ""), p.get("costo_spedizione", 0.0),
            1 if p.get("is_prime") else 0, p.get("immagine_url", ""), p.get("link_affiliato", ""),
            p.get("voto_medio", 4.8), p.get("num_recensioni", 765)
        ))
        conn.commit()

def rimuovi_preferito(asin):
    init_db()
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM preferiti WHERE asin = ?", (asin,))
        conn.commit()
