"""
database.py — SQLite multi-mercado para PerfectStay
"""

import sqlite3, os, json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "perfectstay.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS productos (
    id                  TEXT PRIMARY KEY,
    uri                 TEXT,
    nombre              TEXT,
    pais                TEXT,
    region              TEXT,
    resort              TEXT,
    estrellas           INTEGER,
    tipo                TEXT,
    latitud             REAL,
    longitud            REAL,
    iata_destino        TEXT,
    tripadvisor_rating  REAL,
    tripadvisor_reviews INTEGER,
    foto_url            TEXT,
    topics              TEXT,
    meses               TEXT,
    precio_ref          REAL,
    origen_ref          TEXT,
    noches_ref          INTEGER,
    pension_ref         TEXT,
    market              TEXT DEFAULT 'ES',
    url_prefix          TEXT DEFAULT 'es-ES',
    activo              INTEGER DEFAULT 1,
    primera_vez         TEXT,
    ultima_vez          TEXT
);

CREATE TABLE IF NOT EXISTS precios (
    producto_id     TEXT NOT NULL,
    origen_iata     TEXT NOT NULL,
    noches          INTEGER NOT NULL,
    precio          REAL NOT NULL,       -- precio mínimo
    precio_anterior REAL,
    pension         TEXT,
    top_dates       TEXT,               -- JSON: [{d:"2026-06-15",p:399,r:"2026-06-22"}, ...]
    scrape_ts       TEXT NOT NULL,
    PRIMARY KEY (producto_id, origen_iata, noches)
);

CREATE INDEX IF NOT EXISTS idx_p_market  ON productos(market);
CREATE INDEX IF NOT EXISTS idx_p_activo  ON productos(activo);
CREATE INDEX IF NOT EXISTS idx_pr_prod   ON precios(producto_id);
CREATE INDEX IF NOT EXISTS idx_pr_origen ON precios(origen_iata);
CREATE INDEX IF NOT EXISTS idx_pr_precio ON precios(precio);
"""

PENSION_MAP = {
    "BB":"Breakfast","HB":"Half Board","FB":"Full Board",
    "AI":"All Inclusive","RO":"Room Only","SC":"Room Only",
    "UAI":"All Inclusive","AIL":"All Inclusive","AIS":"All Inclusive",
    "HAI":"All Inclusive","SAI":"All Inclusive",
    "SP":"Half Board","ABF":"Breakfast","CBF":"Breakfast","DB":"Breakfast",
}


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
    print(f"✅ DB: {DB_PATH}")


def upsert_producto(p: dict):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with get_conn() as conn:
        exists = conn.execute("SELECT id FROM productos WHERE id=?", (p["id"],)).fetchone()
        if exists:
            conn.execute("""
                UPDATE productos SET
                    nombre=:nombre, pais=:pais, region=:region, resort=:resort,
                    estrellas=:estrellas, tipo=:tipo, latitud=:latitud, longitud=:longitud,
                    iata_destino=:iata_destino, tripadvisor_rating=:tripadvisor_rating,
                    tripadvisor_reviews=:tripadvisor_reviews, foto_url=:foto_url,
                    topics=:topics, meses=:meses, precio_ref=:precio_ref,
                    origen_ref=:origen_ref, noches_ref=:noches_ref, pension_ref=:pension_ref,
                    market=:market, url_prefix=:url_prefix, activo=1, ultima_vez=:ts
                WHERE id=:id
            """, {**p, "ts": now})
        else:
            conn.execute("""
                INSERT INTO productos (
                    id, uri, nombre, pais, region, resort, estrellas, tipo,
                    latitud, longitud, iata_destino, tripadvisor_rating,
                    tripadvisor_reviews, foto_url, topics, meses,
                    precio_ref, origen_ref, noches_ref, pension_ref,
                    market, url_prefix, activo, primera_vez, ultima_vez
                ) VALUES (
                    :id, :uri, :nombre, :pais, :region, :resort, :estrellas, :tipo,
                    :latitud, :longitud, :iata_destino, :tripadvisor_rating,
                    :tripadvisor_reviews, :foto_url, :topics, :meses,
                    :precio_ref, :origen_ref, :noches_ref, :pension_ref,
                    :market, :url_prefix, 1, :ts, :ts
                )
            """, {**p, "ts": now})


def replace_precios(rows: list[dict], market: str) -> dict:
    """
    Reemplaza precios del mercado.
    Cada row debe tener:
      producto_id, origen_iata, noches, precio, pension,
      top_dates: list of {d, p, r} (date, price, return_date) — top 3 cheapest
    """
    if not rows:
        return {"total": 0, "down": 0, "up": 0}

    now  = datetime.now().strftime("%Y-%m-%d %H:%M")
    down = up = total = 0

    with get_conn() as conn:
        market_ids   = {r["producto_id"] for r in rows}
        placeholders = ",".join("?"*len(market_ids))

        existing = {}
        for row in conn.execute(
            f"SELECT producto_id, origen_iata, noches, precio FROM precios WHERE producto_id IN ({placeholders})",
            list(market_ids)
        ):
            existing[(row["producto_id"], row["origen_iata"], row["noches"])] = row["precio"]

        conn.execute(f"DELETE FROM precios WHERE producto_id IN ({placeholders})", list(market_ids))

        batch = []
        for r in rows:
            key        = (r["producto_id"], r["origen_iata"], r["noches"])
            precio_ant = existing.get(key)
            new_p      = r["precio"]

            if precio_ant is not None and abs(new_p - precio_ant) > 0.5:
                if new_p < precio_ant: down += 1
                else: up += 1

            top_dates_json = json.dumps(r.get("top_dates", []), ensure_ascii=False)

            batch.append((
                r["producto_id"], r["origen_iata"], r["noches"],
                new_p, precio_ant, r.get("pension",""),
                top_dates_json, now
            ))
            total += 1

            if len(batch) >= 500:
                conn.executemany("""
                    INSERT INTO precios (producto_id, origen_iata, noches, precio,
                        precio_anterior, pension, top_dates, scrape_ts)
                    VALUES (?,?,?,?,?,?,?,?)
                """, batch)
                batch = []

        if batch:
            conn.executemany("""
                INSERT INTO precios (producto_id, origen_iata, noches, precio,
                    precio_anterior, pension, top_dates, scrape_ts)
                VALUES (?,?,?,?,?,?,?,?)
            """, batch)

    return {"total": total, "down": down, "up": up}


def mark_inactive(active_ids: set, market: str):
    if not active_ids:
        return
    with get_conn() as conn:
        placeholders = ",".join("?"*len(active_ids))
        conn.execute(
            f"UPDATE productos SET activo=0 WHERE market=? AND id NOT IN ({placeholders})",
            [market] + list(active_ids)
        )
