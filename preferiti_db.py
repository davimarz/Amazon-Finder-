import sqlite3
import json

DB_FILE = "preferiti.db"

def _get_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_db():
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
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
            costo_spedizione REAL,
            voto_medio REAL,
            num_recensioni INTEGER,
            link_affiliato TEXT,
            data_salvataggio TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

def aggiungi_preferito(p):
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO preferiti (
            asin, titolo, immagine_url, prezzo_iniziale, prezzo_finale,
            sconto, sconto_val, is_prime, is_sped_gratis, costo_spedizione,
            voto_medio, num_recensioni, link_affiliato
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        p["asin"],
        p.get("titolo", ""),
        p.get("immagine_url", ""),
        float(p.get("prezzo_iniziale", 0.0)),
        float(p.get("prezzo_finale", 0.0)),
        p.get("sconto", ""),
        int(p.get("sconto_val", 0)),
        1 if p.get("is_prime") else 0,
        1 if p.get("is_sped_gratis") else 0,
        float(p.get("costo_spedizione", 0.0)),
        float(p.get("voto_medio", 4.8)),
        int(p.get("num_recensioni", 765)),
        p.get("link_affiliato", "")
    ))
    conn.commit()
    conn.close()

def rimuovi_preferito(asin):
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM preferiti WHERE asin = ?", (asin,))
    conn.commit()
    conn.close()

def ottieni_tutti_preferiti():
    conn = _get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM preferiti ORDER BY data_salvataggio DESC")
    rows = cursor.fetchall()
    preferiti = []
    for r in rows:
        preferiti.append({
            "asin": r["asin"],
            "titolo": r["titolo"],
            "immagine_url": r["immagine_url"],
            "prezzo_iniziale": r["prezzo_iniziale"],
            "prezzo_finale": r["prezzo_finale"],
            "sconto": r["sconto"],
            "sconto_val": r["sconto_val"],
            "is_prime": bool(r["is_prime"]),
            "is_sped_gratis": bool(r["is_sped_gratis"]),
            "costo_spedizione": r["costo_spedizione"],
            "voto_medio": r["voto_medio"],
            "num_recensioni": r["num_recensioni"],
            "link_affiliato": r["link_affiliato"]
        })
    conn.close()
    return preferiti
