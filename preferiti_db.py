import sqlite3

def init_preferiti_db():
    conn = sqlite3.connect("preferiti.db")
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
            link_affiliato TEXT
        )
    """)
    conn.commit()
    conn.close()

def ottieni_tutti_preferiti():
    init_preferiti_db()
    conn = sqlite3.connect("preferiti.db")
    c = conn.cursor()
    c.execute("SELECT asin, titolo, immagine_url, prezzo_iniziale, prezzo_finale, sconto, is_prime, is_sped_gratis, costo_spedizione, voto_medio, num_recensioni, link_affiliato FROM preferiti")
    rows = c.fetchall()
    conn.close()
    
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
            "link_affiliato": r[11]
        })
    return preferiti

def aggiungi_preferito(p):
    init_preferiti_db()
    conn = sqlite3.connect("preferiti.db")
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO preferiti 
        (asin, titolo, immagine_url, prezzo_iniziale, prezzo_finale, sconto, is_prime, is_sped_gratis, costo_spedizione, voto_medio, num_recensioni, link_affiliato)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        p.get("link_affiliato", "")
    ))
    conn.commit()
    conn.close()

def rimuovi_preferito(asin):
    init_preferiti_db()
    conn = sqlite3.connect("preferiti.db")
    c = conn.cursor()
    c.execute("DELETE FROM preferiti WHERE asin = ?", (asin,))
    conn.commit()
    conn.close()
