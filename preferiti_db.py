import sqlite3
import time

DB_PATH = "preferiti.db"
DB_TIMEOUT_SECONDS = 5


def _connect():
    return sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT_SECONDS)


def init_preferiti_db():
    now = int(time.time())
    with _connect() as conn:
        c = conn.cursor()
        c.execute(
            """
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
            """
        )

        # Migrazione automatica da versioni precedenti.
        c.execute("PRAGMA table_info(preferiti)")
        colonne = [info[1] for info in c.fetchall()]
        if "data_salvataggio" not in colonne:
            c.execute("ALTER TABLE preferiti ADD COLUMN data_salvataggio INTEGER DEFAULT 0")

        # Evita che record legacy con timestamp 0 vengano cancellati immediatamente.
        c.execute(
            "UPDATE preferiti SET data_salvataggio = ? WHERE data_salvataggio IS NULL OR data_salvataggio <= 0",
            (now,),
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_preferiti_data_salvataggio ON preferiti(data_salvataggio)"
        )
        conn.commit()


def pulisci_preferiti_scaduti(ore=24):
    """Cancella i preferiti salvati da più di N ore."""
    init_preferiti_db()
    limite_tempo = int(time.time()) - (ore * 3600)
    with _connect() as conn:
        conn.execute("DELETE FROM preferiti WHERE data_salvataggio < ?", (limite_tempo,))
        conn.commit()


def ottieni_tutti_preferiti():
    pulisci_preferiti_scaduti(ore=24)
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT asin, titolo, immagine_url, prezzo_iniziale, prezzo_finale,
                   sconto, is_prime, is_sped_gratis, costo_spedizione,
                   voto_medio, num_recensioni, link_affiliato, data_salvataggio
            FROM preferiti
            ORDER BY data_salvataggio DESC
            """
        ).fetchall()

    return [
        {
            "asin": r[0],
            "titolo": r[1],
            "immagine_url": r[2],
            "prezzo_iniziale": r[3],
            "prezzo_finale": r[4],
            "sconto": r[5],
            "is_prime": bool(r[6]) if r[6] is not None else None,
            "is_sped_gratis": bool(r[7]) if r[7] is not None else None,
            "costo_spedizione": r[8],
            "voto_medio": r[9],
            "num_recensioni": r[10],
            "link_affiliato": r[11],
            "data_salvataggio": r[12],
        }
        for r in rows
    ]


def aggiungi_preferito(p):
    init_preferiti_db()
    timestamp_ora = int(time.time())

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO preferiti
                (asin, titolo, immagine_url, prezzo_iniziale, prezzo_finale, sconto,
                 is_prime, is_sped_gratis, costo_spedizione, voto_medio, num_recensioni,
                 link_affiliato, data_salvataggio)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(asin) DO UPDATE SET
                titolo = excluded.titolo,
                immagine_url = excluded.immagine_url,
                prezzo_iniziale = excluded.prezzo_iniziale,
                prezzo_finale = excluded.prezzo_finale,
                sconto = excluded.sconto,
                is_prime = excluded.is_prime,
                is_sped_gratis = excluded.is_sped_gratis,
                costo_spedizione = excluded.costo_spedizione,
                voto_medio = excluded.voto_medio,
                num_recensioni = excluded.num_recensioni,
                link_affiliato = excluded.link_affiliato,
                data_salvataggio = excluded.data_salvataggio
            """,
            (
                p["asin"],
                p.get("titolo", ""),
                p.get("immagine_url", ""),
                p.get("prezzo_iniziale", 0.0),
                p.get("prezzo_finale", 0.0),
                p.get("sconto", ""),
                1 if p.get("is_prime") is True else (0 if p.get("is_prime") is False else None),
                1 if p.get("is_sped_gratis") is True else (0 if p.get("is_sped_gratis") is False else None),
                p.get("costo_spedizione"),
                p.get("voto_medio"),
                p.get("num_recensioni"),
                p.get("link_affiliato", ""),
                timestamp_ora,
            ),
        )
        conn.commit()


def rimuovi_preferito(asin):
    init_preferiti_db()
    with _connect() as conn:
        conn.execute("DELETE FROM preferiti WHERE asin = ?", (asin,))
        conn.commit()
