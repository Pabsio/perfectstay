"""
app.py — Dashboard Flask para PerfectStay
Ejecutar: python3 app.py → http://localhost:5001
"""

from flask import Flask, render_template, request, jsonify, g
import sqlite3, os, json

app     = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "perfectstay.db")

AIRPORT_LABELS = {
    "MAD": "Madrid", "BCN": "Barcelona", "BIO": "Bilbao",
    "SVQ": "Sevilla", "VLC": "Valencia", "AGP": "Málaga",
    "ALC": "Alicante", "OVD": "Asturias", "SCQ": "Santiago",
    "SDR": "Santander", "ZAZ": "Zaragoza", "GRX": "Granada", "PMI": "Mallorca",
}

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db: db.close()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stats")
def api_stats():
    db = get_db()
    productos    = db.execute("SELECT COUNT(*) FROM productos WHERE activo=1").fetchone()[0]
    total_precio = db.execute("SELECT COUNT(*) FROM precios").fetchone()[0]
    precio_min   = db.execute("SELECT MIN(precio) FROM precios").fetchone()[0]
    precio_med   = db.execute("SELECT ROUND(AVG(precio),0) FROM precios").fetchone()[0]

    por_pais = db.execute("""
        SELECT pais, COUNT(*) as n FROM productos WHERE activo=1
        GROUP BY pais ORDER BY n DESC LIMIT 10
    """).fetchall()

    return jsonify({
        "productos":     productos,
        "total_precios": total_precio,
        "precio_min":    precio_min,
        "precio_medio":  precio_med,
        "por_pais":      [dict(r) for r in por_pais],
    })


@app.route("/api/productos")
def api_productos():
    db = get_db()

    pais        = request.args.get("pais", "")
    region      = request.args.get("region", "")
    estrellas   = request.args.get("estrellas", "")
    origen      = request.args.get("origen", "")
    noches      = request.args.get("noches", "")
    precio_max  = request.args.get("precio_max", "")
    precio_min  = request.args.get("precio_min", "")
    pension     = request.args.get("pension", "")
    search      = request.args.get("q", "")
    orden       = request.args.get("orden", "precio_min_asc")
    page        = int(request.args.get("page", 1))
    per_page    = int(request.args.get("per_page", 40))

    precio_where  = ["1=1"]
    precio_params = []

    if origen:
        precio_where.append("pr.origen_iata = ?")
        precio_params.append(origen)
    if noches:
        precio_where.append("pr.noches = ?")
        precio_params.append(int(noches))
    if precio_min:
        precio_where.append("pr.precio >= ?")
        precio_params.append(float(precio_min))
    if precio_max:
        precio_where.append("pr.precio <= ?")
        precio_params.append(float(precio_max))
    if pension:
        precio_where.append("pr.pension = ?")
        precio_params.append(pension)

    prod_where  = ["p.activo = 1"]
    prod_params = []

    if pais:
        prod_where.append("p.pais = ?")
        prod_params.append(pais)
    if region:
        prod_where.append("p.region = ?")
        prod_params.append(region)
    if estrellas:
        prod_where.append("p.estrellas = ?")
        prod_params.append(int(estrellas))
    if search:
        prod_where.append("(p.nombre LIKE ? OR p.resort LIKE ? OR p.pais LIKE ?)")
        s = f"%{search}%"
        prod_params.extend([s, s, s])

    precio_filter = " AND ".join(precio_where)
    prod_filter   = " AND ".join(prod_where)

    order_map = {
        "precio_min_asc":  "precio_actual ASC",
        "precio_min_desc": "precio_actual DESC",
        "estrellas_desc":  "p.estrellas DESC, precio_actual ASC",
        "ta_rating":       "p.tripadvisor_rating DESC",
        "nombre":          "p.nombre ASC",
    }
    order_clause = order_map.get(orden, "precio_actual ASC")

    all_params = precio_params + prod_params

    sql = f"""
        SELECT
            p.id, p.uri, p.nombre, p.pais, p.region, p.resort,
            p.estrellas, p.tipo, p.foto_url, p.topics,
            p.tripadvisor_rating, p.tripadvisor_reviews,
            p.iata_destino,
            MIN(pr.precio)    AS precio_actual,
            pr.origen_iata    AS mejor_origen,
            pr.noches         AS mejor_noches,
            pr.fecha_salida   AS mejor_fecha,
            pr.pension        AS mejor_pension,
            pr.precio_anterior AS precio_anterior
        FROM productos p
        JOIN precios pr ON pr.producto_id = p.id
        WHERE {precio_filter} AND {prod_filter}
        GROUP BY p.id
        ORDER BY {order_clause}
    """

    total  = db.execute(f"SELECT COUNT(*) FROM ({sql})", all_params).fetchone()[0]
    offset = (page - 1) * per_page
    rows   = db.execute(sql + f" LIMIT {per_page} OFFSET {offset}", all_params).fetchall()

    def row_to_dict(r):
        d = dict(r)
        try:    d["topics"] = json.loads(d.get("topics") or "[]")
        except: d["topics"] = []
        d["mejor_origen_label"] = AIRPORT_LABELS.get(d.get("mejor_origen", ""), d.get("mejor_origen", ""))
        d["url"] = f"https://holidaypirates.perfectstay.com/es-ES/{d['uri']}"
        # Badge bajada de precio
        ant = d.get("precio_anterior")
        act = d.get("precio_actual")
        if ant and act and act < ant:
            d["bajada_pct"] = round((ant - act) / ant * 100)
        else:
            d["bajada_pct"] = None
        return d

    return jsonify({
        "total":  total,
        "page":   page,
        "pages":  (total + per_page - 1) // per_page,
        "items":  [row_to_dict(r) for r in rows],
    })


@app.route("/api/filtros")
def api_filtros():
    db = get_db()

    def vals(col, table="productos", condition="activo=1"):
        rows = db.execute(
            f"SELECT DISTINCT {col} FROM {table} WHERE {condition} AND {col} != '' ORDER BY {col}"
        ).fetchall()
        return [r[0] for r in rows if r[0]]

    noches_raw   = db.execute("SELECT DISTINCT noches FROM precios WHERE noches IS NOT NULL ORDER BY noches").fetchall()
    pension_raw  = db.execute("SELECT DISTINCT pension FROM precios WHERE pension != '' ORDER BY pension").fetchall()
    origenes_raw = db.execute("SELECT DISTINCT origen_iata FROM precios WHERE origen_iata != '' ORDER BY origen_iata").fetchall()

    origenes = [
        {"code": r[0], "label": AIRPORT_LABELS.get(r[0], r[0])}
        for r in origenes_raw
    ]

    return jsonify({
        "paises":    vals("pais"),
        "regiones":  vals("region"),
        "estrellas": vals("estrellas"),
        "noches":    [r[0] for r in noches_raw],
        "pensiones": [r[0] for r in pension_raw],
        "origenes":  origenes,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5001)
