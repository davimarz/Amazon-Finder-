import sqlite3
import json

DB_FILE = "preferiti.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS preferiti (
            asin TEXT PRIMARY KEY,
            titolo TEXT,
            immagine_url TEXT,
            prezzo_iniziale REAL,
            prezzo_finale REAL,
            sconto TEXT,
            sconto_val INTEGER,
            is_prime INTEGER,
            is_sped_gratis INTEGER,
            info_spedizione TEXT,
            costo_spedizione REAL,
            voto_medio REAL,
            num_recensioni INTEGER,
            link_affiliato TEXT,
            raw_data TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def ottieni_tutti_preferiti():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM preferiti")
    rows = c.fetchall()
    conn.close()
    
    preferiti = []
    for r in rows:
        item = dict(r)
        item["is_prime"] = bool(item.get("is_prime", 0))
        item["is_sped_gratis"] = bool(item.get("is_sped_gratis", 0))
        preferiti.append(item)
    return preferiti

def aggiungi_preferito(p):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO preferiti (
            asin, titolo, immagine_url, prezzo_iniziale, prezzo_finale,
            sconto, sconto_val, is_prime, is_sped_gratis, info_spedizione,
            costo_spedizione, voto_medio, num_recensioni, link_affiliato, raw_data
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        p.get("asin"),
        p.get("titolo"),
        p.get("immagine_url"),
        float(p.get("prezzo_iniziale", 0.0)),
        float(p.get("prezzo_finale", 0.0)),
        p.get("sconto", ""),
        int(p.get("sconto_val", 0)),
        1 if p.get("is_prime") else 0,
        1 if p.get("is_sped_gratis") else 0,
        p.get("info_spedizione", ""),
        float(p.get("costo_spedizione", 0.0)),
        float(p.get("voto_medio", 4.8)),
        int(p.get("num_recensioni", 765)),
        p.get("link_affiliato", ""),
        json.dumps(p)
    ))
    conn.commit()
    conn.close()

def rimuovi_preferito(asin):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM preferiti WHERE asin = ?", (asin,))
    conn.commit()
    conn.close()
