"""
build.py — PerfectStay board estático
- Filtros como pills (sin dropdowns)
- Market pills: ES / FR / IT
- Region tabs por mercado
- Sin stats bar, sin price drop filter
- Todo en una página (sin paginación)
"""

import sqlite3, json, os
from datetime import datetime

DB_PATH  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "perfectstay.db")
OUT_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
OUT_FILE = os.path.join(OUT_DIR, "index.html")

AIRPORT_LABELS = {
    "MAD":"Madrid","BCN":"Barcelona","BIO":"Bilbao","SVQ":"Sevilla",
    "VLC":"Valencia","AGP":"Málaga","ALC":"Alicante","OVD":"Asturias",
    "SCQ":"Santiago","SDR":"Santander","ZAZ":"Zaragoza","GRX":"Granada","PMI":"Mallorca",
    # FR airports
    "CDG":"Paris","ORY":"Paris Orly","LYS":"Lyon","MRS":"Marseille",
    "NCE":"Nice","TLS":"Toulouse","BOD":"Bordeaux","NTE":"Nantes","LIL":"Lille",
    # IT airports
    "FCO":"Roma","MXP":"Milano","LIN":"Milano Linate","BGY":"Bergamo",
    "VCE":"Venezia","NAP":"Napoli","BLQ":"Bologna","CTA":"Catania","PMO":"Palermo",
}

PENSION_EN = {
    "All Inclusive":"All Inclusive","Half Board":"Half Board",
    "Full Board":"Full Board","Breakfast":"Breakfast","Room Only":"Room Only",
    "Todo Incluido":"All Inclusive","Media Pensión":"Half Board",
    "Pensión Completa":"Full Board","Desayuno":"Breakfast","Solo Alojamiento":"Room Only",
    "Tout inclus":"All Inclusive","Demi-pension":"Half Board",
    "Pension complète":"Full Board","Petit-déjeuner":"Breakfast","Logement seul":"Room Only",
    "Tutto incluso":"All Inclusive","Mezza pensione":"Half Board",
    "Pensione completa":"Full Board","Prima colazione":"Breakfast","Solo pernottamento":"Room Only",
    "Pensione come da programma":"Full Board",
    "UAI":"All Inclusive","AIL":"All Inclusive","AIS":"All Inclusive",
    "HAI":"All Inclusive","SAI":"All Inclusive",
    "SP":"Half Board","ABF":"Breakfast","CBF":"Breakfast","DB":"Breakfast","UHB":"Half Board","GGBB":"Breakfast",
    "UHB":"Half Board","GGBB":"Breakfast",
}

PENSION_SCORE = {
    "All Inclusive":15,"Half Board":10,"Full Board":12,"Breakfast":5,"Room Only":0,
    "Todo Incluido":15,"Tout inclus":15,"Tutto incluso":15,
    "Media Pensión":10,"Demi-pension":10,"Mezza pensione":10,
    "Pensión Completa":12,"Pension complète":12,"Pensione completa":12,"Pensione come da programma":12,
    "Desayuno":5,"Petit-déjeuner":5,"Prima colazione":5,
    "Solo Alojamiento":0,"Logement seul":0,"Solo pernottamento":0,
    "UAI":15,"AIL":15,"AIS":15,"HAI":15,"SAI":15,
    "SP":10,"ABF":5,"CBF":5,"DB":5,
    "UHB":10,"GGBB":5,
}

TOPICS_EN = {
    # Spanish
    "City break":"City Break","Romántico":"Romantic","Lujo":"Luxury",
    "Todo incluido":"All Inclusive","Familia":"Family","Club":"Club",
    "Golf":"Golf","Safari":"Safari","Crucero":"Cruise","Circuito":"Tour",
    "Combinado":"Combined","Estancia corta":"Short Stay","Deporte":"Sport",
    "Descubrimiento ":"Discovery","Sol y mar":"Sun & Sea","Piscina":"Pool",
    "Solo para adultos":"Adults Only","Spa y Bienestar":"Spa & Wellness",
    "Viaje combinado":"Combined","No se lo pierda":"Must-see","Premium":"Premium","Upgrade":"Upgrade",
    # French
    "Romantique":"Romantic","Luxe":"Luxury","Tout inclus":"All Inclusive",
    "Famille":"Family","Croisière":"Cruise","Circuit":"Tour","Combiné":"Combined",
    "Court séjour":"Short Stay","Découverte":"Discovery","Mer et soleil":"Sun & Sea",
    "Piscine":"Pool","Adultes uniquement":"Adults Only","Bien-être et Spa":"Spa & Wellness",
    "Aquaparc":"Water Park","Autotour":"Self-Drive","Incontournables":"Must-see",
    "Surclassement":"Upgrade","Sport":"Sport",
    # Italian
    "Romantico":"Romantic","Lusso":"Luxury","Crociera":"Cruise","Circuito":"Tour",
    "Combinato":"Combined","Soggiorno breve":"Short Stay","Scoperta":"Discovery",
    "Mare e sole":"Sun & Sea","Piscina":"Pool","Solo per adulti":"Adults Only",
    "Benessere e Spa":"Spa & Wellness","Famiglia":"Family","Da non perdere":"Must-see",
    "Viaggio in auto a noleggio":"Self-Drive","Sport":"Sport",
    # Already English
    "All inclusive":"All Inclusive","Golf":"Golf","Safari":"Safari","Club":"Club","Premium":"Premium",
}

REGION_MAP = {
    "España":"Spain","France":"Europe","Francia":"Europe","Italia":"Europe","Italy":"Europe",
    "Grecia":"Europe","Greece":"Europe","Croacia":"Europe","Croatia":"Europe",
    "Portugal":"Europe","Reino Unido":"Europe","United Kingdom":"Europe",
    "Alemania":"Europe","Germany":"Europe","Allemagne":"Europe",
    "Austria":"Europe","Bélgica":"Europe","Belgique":"Europe","Belgium":"Europe",
    "Países Bajos":"Europe","Pays-Bas":"Europe","Netherlands":"Europe",
    "Polonia":"Europe","Pologne":"Europe","Poland":"Europe",
    "República Checa":"Europe","Tchéquie":"Europe","Czech Republic":"Europe",
    "Malta":"Europe","Chipre":"Europe","Chypre":"Europe","Cyprus":"Europe",
    "Turquía":"Europe","Turquie":"Europe","Turkey":"Europe",
    "Túnez":"Europe","Tunisie":"Europe","Tunisia":"Europe",
    "Marruecos":"Europe","Maroc":"Europe","Morocco":"Europe",
    "Egipto":"Middle East & Africa","Égypte":"Middle East & Africa","Egypt":"Middle East & Africa",
    "Emiratos Árabes Unidos":"Middle East & Africa","Émirats arabes unis":"Middle East & Africa",
    "Isla Mauricio":"Middle East & Africa","Île Maurice":"Middle East & Africa","Mauritius":"Middle East & Africa",
    "Seychelles":"Middle East & Africa","Tanzania":"Middle East & Africa","Tanzanie":"Middle East & Africa",
    "La Reunión":"Middle East & Africa","La Réunion":"Middle East & Africa",
    "República Dominicana":"Caribbean","République dominicaine":"Caribbean","Dominican Republic":"Caribbean",
    "Jamaica":"Caribbean","Antillas Neerlandesas":"Caribbean","Antilles néerlandaises":"Caribbean",
    "Cuba":"Caribbean",
    "México":"Americas","Mexique":"Americas","Mexico":"Americas",
    "Brasil":"Americas","Brésil":"Americas","Brazil":"Americas",
    "Argentina":"Americas","Argentine":"Americas",
    "Colombia":"Americas","Colombie":"Americas",
    "Costa Rica":"Americas","Panamá":"Americas","Panama":"Americas",
    "Canadá":"Americas","Canada":"Americas","Estados Unidos":"Americas","États-Unis":"Americas","USA":"Americas",
    "Maldivas":"Asia & Pacific","Maldives":"Asia & Pacific",
    "Indonesia":"Asia & Pacific","Indonésie":"Asia & Pacific",
    "Tailandia":"Asia & Pacific","Thaïlande":"Asia & Pacific","Thailand":"Asia & Pacific",
    "Filipinas":"Asia & Pacific","Philippines":"Asia & Pacific",
    "Vietnam":"Asia & Pacific","Viet Nam":"Asia & Pacific",
    "Malasia":"Asia & Pacific","Malaisie":"Asia & Pacific","Malaysia":"Asia & Pacific",
    "Camboya":"Asia & Pacific","Cambodge":"Asia & Pacific","Cambodia":"Asia & Pacific",
    "Laos":"Asia & Pacific","India":"Asia & Pacific","Inde":"Asia & Pacific",
    "Sri Lanka":"Asia & Pacific","Japón":"Asia & Pacific","Japon":"Asia & Pacific","Japan":"Asia & Pacific",
    "Corea del Sur":"Asia & Pacific","Corée du Sud":"Asia & Pacific","South Korea":"Asia & Pacific",
    "China":"Asia & Pacific","Chine":"Asia & Pacific",
    "Singapur":"Asia & Pacific","Singapour":"Asia & Pacific","Singapore":"Asia & Pacific",
    "Taiwán":"Asia & Pacific","Taïwan":"Asia & Pacific","Taiwan":"Asia & Pacific",
}

PREMIUM_COUNTRIES = {
    "Maldivas","Maldives","Seychelles","Isla Mauricio","Île Maurice","Mauritius",
    "La Reunión","La Réunion","Indonesia","Indonésie","Tailandia","Thaïlande","Thailand",
    "Japón","Japon","Japan","Tanzania","Tanzanie",
}

REGION_ORDER = ["Spain","Europe","Caribbean","Middle East & Africa","Asia & Pacific","Americas","Other"]

NIGHTS_GROUPS = [
    ("1–3",  1,  3),
    ("4–6",  4,  6),
    ("7–10", 7, 10),
    ("11+", 11, 99),
]

STARS_GROUPS = ["3","4","5"]


def compute_score(p):
    stars        = float(p.get("estrellas") or 0)
    ta           = float(p.get("tripadvisor_rating") or 0)
    precio       = float(p.get("precio_actual") or 0)
    noches       = float(p.get("mejor_noches") or 1) or 1
    pension      = p.get("mejor_pension") or ""
    pais         = p.get("pais") or ""
    ant          = float(p.get("precio_anterior") or 0)
    precio_noche = precio / noches if precio else 999

    base        = (stars * 4) + (ta * 10)
    bon_pension = PENSION_SCORE.get(pension, 0)
    bon_desc    = 0
    if ant and precio and precio < ant:
        bon_desc = min((ant - precio) / ant * 100 * 0.4, 15)
    bon_premium = 8 if pais in PREMIUM_COUNTRIES else 0
    pen_precio  = min(precio_noche / 12, 20)

    return base + bon_pension + bon_desc + bon_premium - pen_precio


def normalize_scores(products):
    by_region = {}
    for p in products:
        by_region.setdefault(p.get("_region","Other"), []).append(p)
    for items in by_region.values():
        scores   = [p["_score_raw"] for p in items]
        mn, mx   = min(scores), max(scores)
        rng      = mx - mn or 1
        for p in items:
            p["score"] = round((p["_score_raw"] - mn) / rng * 100)


def load_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Load products
    prod_rows = conn.execute("""
        SELECT id, uri, nombre, pais, region AS db_region, resort,
               estrellas, tipo, foto_url, topics,
               tripadvisor_rating, tripadvisor_reviews,
               market, url_prefix
        FROM productos WHERE activo = 1
    """).fetchall()

    # Load all prices grouped by product
    price_rows = conn.execute("""
        SELECT producto_id, origen_iata, noches, precio, precio_anterior, pension, top_dates
        FROM precios
        ORDER BY producto_id, precio ASC
    """).fetchall()
    conn.close()

    # Index prices by product_id
    prices_by_product = {}
    for pr in price_rows:
        pid = pr["producto_id"]
        if pid not in prices_by_product:
            prices_by_product[pid] = []
        try:
            td = json.loads(pr["top_dates"] or "[]")
        except Exception:
            td = []
        prices_by_product[pid].append({
            "o":  pr["origen_iata"],
            "n":  int(pr["noches"] or 0),
            "p":  float(pr["precio"] or 0),
            "pa": float(pr["precio_anterior"]) if pr["precio_anterior"] else None,
            "b":  pr["pension"] or "",
            "td": td,
        })

    rows = prod_rows

    products = []
    for r in rows:
        d = dict(r)
        try:
            raw_topics = json.loads(d.get("topics") or "[]")
            d["topics"] = list(dict.fromkeys(
                TOPICS_EN.get(t.strip(), t.strip()) for t in raw_topics if t and t.strip()
            ))
        except:
            d["topics"] = []

        d["market"]   = d.get("market") or "ES"
        d["_region"]  = REGION_MAP.get(d.get("pais") or "", "Other")
        d["url"]      = f"https://holidaypirates.perfectstay.com/{d.get('url_prefix','es-ES')}/{d['uri']}"

        # Attach all prices for this product
        pid    = d["id"]
        plist  = prices_by_product.get(pid, [])
        d["prices"] = plist

        # Global min price (for default display and score)
        if plist:
            best        = min(plist, key=lambda x: x["p"])
            d["precio_actual"]   = best["p"]
            d["mejor_origen"]    = best["o"]
            d["mejor_noches"]    = best["n"]
            d["mejor_pension"]   = best["b"]
            d["precio_anterior"] = best["pa"]
        else:
            d["precio_actual"] = d["mejor_origen"] = d["mejor_noches"] = None
            d["mejor_pension"] = d["precio_anterior"] = None

        noches = float(d.get("mejor_noches") or 1) or 1
        precio = float(d.get("precio_actual") or 0)
        d["precio_noche"]  = round(precio / noches) if precio else None
        ant, act           = d.get("precio_anterior"), d.get("precio_actual")
        d["bajada_pct"]    = round((float(ant)-float(act))/float(ant)*100) if ant and act and float(act)<float(ant) else None
        d["pension_en"]    = PENSION_EN.get(d.get("mejor_pension") or "", d.get("mejor_pension") or "")
        d["origen_label"]  = AIRPORT_LABELS.get(d.get("mejor_origen") or "", d.get("mejor_origen") or "")
        d["_score_raw"]    = compute_score(d)
        products.append(d)

    normalize_scores(products)
    for p in products:
        p["region_tab"] = p.pop("_region")
        del p["_score_raw"]

    products.sort(key=lambda x: x.get("score", 0), reverse=True)

    # Filtros únicos por mercado
    origins_by_market = {}
    boards_by_market  = {}
    for p in products:
        mkt = p.get("market","ES")
        for pr in p.get("prices", []):
            if pr.get("o"):
                origins_by_market.setdefault(mkt, set()).add(pr["o"])
            # Try pension from 'b' field, fallback to first top_date's 'b'
            b_raw = pr.get("b","")
            if not b_raw:
                tds = pr.get("td", [])
                if tds: b_raw = tds[0].get("b","")
            if b_raw:
                pen_en = PENSION_EN.get(b_raw, b_raw)
                if pen_en and pen_en not in ("","Unknown"):
                    boards_by_market.setdefault(mkt, set()).add(pen_en)

    # Noches únicas por mercado
    noches_by_market = {}
    for p in products:
        mkt = p.get("market","ES")
        for pr in p.get("prices", []):
            if pr.get("n"): noches_by_market.setdefault(mkt, set()).add(int(pr["n"]))

    paises = sorted(set(p.get("pais") or "" for p in products if p.get("pais")))

    # Convert sets to sorted lists with labels
    def origins_for(mkt):
        codes = sorted(origins_by_market.get(mkt, set()))
        return [{"code": c, "label": AIRPORT_LABELS.get(c, c)} for c in codes]

    def boards_for(mkt):
        return sorted(boards_by_market.get(mkt, set()))

    def noches_for(mkt):
        return sorted(noches_by_market.get(mkt, set()))

    # Months from top_dates
    months_by_market = {}
    for p in products:
        mkt = p.get("market","ES")
        for pr in p.get("prices", []):
            for td in pr.get("td", []):
                d = td.get("d","")
                if d and len(d) >= 7:
                    months_by_market.setdefault(mkt, set()).add(d[:7])

    def months_for(mkt):
        return sorted(months_by_market.get(mkt, set()))

    return {
        "products": products,
        "stats":    {"total": len(products), "generado": datetime.now().strftime("%d/%m/%Y %H:%M")},
        "filters":  {
            "origins_by_market": {m: origins_for(m) for m in ["ES","FR","IT"]},
            "boards_by_market":  {m: boards_for(m)  for m in ["ES","FR","IT"]},
            "noches_by_market":  {m: noches_for(m)  for m in ["ES","FR","IT"]},
            "months_by_market":  {m: months_for(m)  for m in ["ES","FR","IT"]},
            "countries": paises,
        }
    }


def build():
    print("📦 Reading database...")
    data     = load_data()
    stats    = data["stats"]
    data_js  = json.dumps(data, ensure_ascii=False)

    os.makedirs(OUT_DIR, exist_ok=True)

    html = HTML_TEMPLATE\
        .replace("__DATA__",      data_js)\
        .replace("__GENERATED__", stats["generado"])\
        .replace("__TOTAL__",     str(stats["total"]))

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ {OUT_FILE} ({os.path.getsize(OUT_FILE)//1024} KB, {stats['total']} deals)")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Travel Deals · HolidayPirates</title>
<link href="https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --hp-purple:#6A3460;--hp-purple-l:#f3eef2;--hp-purple-m:#d4b8cf;
  --hp-black:#333333;--hp-white:#ffffff;
  --hp-blue:#7ac3dd;--hp-lilac:#a685a0;--hp-green:#a9d380;
  --hp-pink:#f79f9d;--hp-orange:#febb8c;--hp-yellow:#fcd988;
  --bg:#f7f4f6;--surface:#fff;--border:#e8e0e6;--text:#333333;
  --muted:#8a7a87;--radius:12px;
  --shadow:0 1px 4px rgba(106,52,96,.08);
  --shadow-md:0 6px 20px rgba(106,52,96,.14);
}
body{font-family:"Open Sans",sans-serif;background:var(--bg);color:var(--text);font-size:14px;-webkit-font-smoothing:antialiased}
a{text-decoration:none}
button{cursor:pointer;font:inherit;border:none;background:none}

/* ── Topbar ── */
.topbar{
  background:var(--hp-purple);padding:0 24px;height:54px;
  display:flex;align-items:center;justify-content:space-between;
  position:sticky;top:0;z-index:100;
  box-shadow:0 2px 8px rgba(106,52,96,.25);
}
.topbar-brand{display:flex;align-items:center;gap:10px;color:#fff}
.topbar-brand h1{font-size:16px;font-weight:700;letter-spacing:-.01em}
.topbar-meta{font-size:12px;color:var(--hp-purple-m)}
.topbar-right{display:flex;align-items:center;gap:12px}

/* View toggle */
.view-toggle{display:flex;gap:4px}
.view-btn-toggle{
  padding:5px 10px;border-radius:8px;font-size:13px;color:rgba(255,255,255,.6);
  transition:all .15s;
}
.view-btn-toggle.on{background:rgba(255,255,255,.2);color:#fff}
.view-btn-toggle:hover{color:#fff}

/* ── Filter bar ── */
.filterbar{
  background:var(--surface);border-bottom:1px solid var(--border);
  padding:10px 24px;display:flex;flex-direction:column;gap:8px;
  position:sticky;top:54px;z-index:99;
  box-shadow:0 2px 6px rgba(106,52,96,.06);
}
.filter-row{display:flex;align-items:center;gap:7px;flex-wrap:wrap}
.filter-label{
  font-size:10px;font-weight:700;text-transform:uppercase;
  letter-spacing:.08em;color:var(--hp-purple);white-space:nowrap;min-width:55px;
}

/* Pills */
.pill{
  padding:5px 13px;border-radius:20px;font-size:13px;font-weight:600;
  background:var(--bg);border:1.5px solid var(--border);color:var(--muted);
  cursor:pointer;transition:all .15s;white-space:nowrap;
}
.pill:hover{border-color:var(--hp-purple);color:var(--hp-purple)}
.pill.on{background:var(--hp-purple);border-color:var(--hp-purple);color:#fff}
.pill.market{font-size:12px;padding:4px 11px}

/* Search */
.search-wrap{position:relative;flex:1;max-width:300px}
.search-wrap input{
  width:100%;padding:6px 12px 6px 30px;border:1.5px solid var(--border);
  border-radius:20px;font:inherit;font-size:13px;background:var(--bg);outline:none;
  transition:border-color .15s;
}
.search-wrap input:focus{border-color:var(--hp-purple)}
.search-icon{position:absolute;left:9px;top:50%;transform:translateY(-50%);color:var(--muted);font-size:13px;pointer-events:none}

/* Selects */
.hp-select{
  padding:5px 11px;border:1.5px solid var(--border);border-radius:20px;
  font:inherit;font-size:13px;background:var(--bg);outline:none;
  color:var(--text);cursor:pointer;transition:border-color .15s;
}
.hp-select:focus{border-color:var(--hp-purple)}

.rc{font-size:12px;color:var(--muted);margin-left:auto;white-space:nowrap}

/* ── Region tabs ── */
.region-tabs{padding:10px 24px 0;display:flex;gap:6px;flex-wrap:wrap}
.rtab{
  padding:5px 14px;border-radius:20px;font-size:13px;font-weight:600;
  background:var(--surface);border:1.5px solid var(--border);color:var(--muted);
  cursor:pointer;transition:all .15s;white-space:nowrap;
}
.rtab:hover{border-color:var(--hp-purple);color:var(--hp-purple)}
.rtab.on{background:var(--hp-purple-l);border-color:var(--hp-purple);color:var(--hp-purple)}
.rtab .n{font-size:11px;margin-left:4px;opacity:.6}

/* ── GRID VIEW ── */
.grid-wrap{padding:12px 24px 32px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(275px,1fr));gap:13px}

.card{
  background:var(--surface);border-radius:var(--radius);overflow:hidden;
  box-shadow:var(--shadow);transition:box-shadow .2s,transform .2s;
  display:flex;flex-direction:column;border:1px solid var(--border);
}
.card:hover{box-shadow:var(--shadow-md);transform:translateY(-2px)}
.card-img{height:155px;overflow:hidden;position:relative;flex-shrink:0;background:var(--bg)}
.card-img img{width:100%;height:100%;object-fit:cover;display:block}
.card-img .no-img{width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-size:40px}
.score-pill{
  position:absolute;top:8px;left:8px;
  background:rgba(51,51,51,.7);backdrop-filter:blur(6px);color:#fff;
  font-size:11px;font-weight:700;padding:3px 8px;border-radius:7px;
  display:flex;align-items:center;gap:5px;
}
.sdot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.s-hi{background:#a9d380}.s-mid{background:#febb8c}.s-lo{background:#a685a0}
.drop-pill{
  position:absolute;top:8px;right:8px;
  background:#a9d380;color:#fff;
  font-size:11px;font-weight:700;padding:3px 8px;border-radius:7px;
}
.card-body{padding:11px 13px;flex:1;display:flex;flex-direction:column;gap:4px}
.card-name{font-size:13px;font-weight:700;line-height:1.3;color:var(--text)}
.card-loc{font-size:12px;color:var(--muted)}
.card-badges{display:flex;flex-wrap:wrap;gap:4px;margin-top:2px}
.bdg{font-size:11px;padding:2px 8px;border-radius:6px;font-weight:600}
.bdg-board{background:var(--hp-purple-l);color:var(--hp-purple)}
.bdg-stars{background:#fff9e6;color:#9a7206}
.bdg-ta{background:#f0fae6;color:#3d6b1a}
.card-footer{
  padding:9px 13px 12px;border-top:1px solid var(--border);
  display:flex;align-items:flex-end;justify-content:space-between;margin-top:auto;
}
.price-from{font-size:10px;color:var(--muted);margin-bottom:1px}
.price-main{font-size:23px;font-weight:800;line-height:1;color:var(--hp-purple)}
.price-sub{font-size:11px;color:var(--muted);margin-top:2px}
.price-old{font-size:11px;color:var(--muted);text-decoration:line-through;margin-top:1px}
.cta-btn{
  padding:7px 13px;background:var(--hp-purple);color:#fff;
  border-radius:9px;font-size:12px;font-weight:700;white-space:nowrap;
  transition:background .15s;
}
.cta-btn:hover{background:#4e2647;text-decoration:none}

/* ── LIST VIEW ── */
.list{display:flex;flex-direction:column;gap:0}
.list-item{
  background:var(--surface);border-bottom:1px solid var(--border);
  display:flex;align-items:stretch;gap:0;
  transition:background .15s;
}
.list-item:first-child{border-top:1px solid var(--border);border-radius:var(--radius) var(--radius) 0 0;overflow:hidden}
.list-item:last-child{border-radius:0 0 var(--radius) var(--radius);overflow:hidden}
.list-item:hover{background:#faf7f9}
.list-thumb{width:110px;min-width:110px;height:80px;overflow:hidden;position:relative;flex-shrink:0}
.list-thumb img{width:100%;height:100%;object-fit:cover;display:block}
.list-thumb .no-img{width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-size:28px;background:var(--bg)}
.list-score{
  position:absolute;bottom:4px;left:4px;
  background:rgba(51,51,51,.7);color:#fff;
  font-size:10px;font-weight:700;padding:2px 6px;border-radius:5px;
  display:flex;align-items:center;gap:3px;
}
.list-body{flex:1;padding:10px 14px;display:flex;flex-direction:column;justify-content:center;gap:3px;min-width:0}
.list-name{font-size:13px;font-weight:700;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.list-loc{font-size:12px;color:var(--muted)}
.list-desc{font-size:12px;color:var(--muted);line-height:1.4;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.list-badges{display:flex;flex-wrap:wrap;gap:3px;margin-top:2px}
.list-right{
  padding:10px 16px;display:flex;flex-direction:column;
  align-items:flex-end;justify-content:center;gap:4px;
  min-width:160px;border-left:1px solid var(--border);
}
.list-drop{font-size:11px;font-weight:700;color:#3d6b1a;background:#f0fae6;padding:2px 7px;border-radius:5px;align-self:flex-end}

.empty{text-align:center;padding:80px 20px;color:var(--muted)}
.empty .icon{font-size:52px;margin-bottom:12px}
.empty p{font-size:15px}

  #auth-gate{position:fixed;inset:0;background:var(--bg);z-index:9999;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:20px}
  #auth-gate .auth-box{background:#fff;border-radius:18px;padding:40px 48px;text-align:center;box-shadow:0 8px 40px rgba(106,52,96,.12);max-width:380px;width:90%}
  #auth-gate .auth-title{font-size:22px;font-weight:800;color:var(--hp);margin-bottom:8px}
  #auth-gate .auth-sub{font-size:13px;color:var(--muted);margin-bottom:28px}
  #auth-gate .auth-btn{width:100%;font-family:inherit;font-size:14px;font-weight:700;padding:13px;border-radius:20px;border:none;background:var(--hp);color:#fff;cursor:pointer;transition:opacity .15s;display:flex;align-items:center;justify-content:center;gap:10px}
  #auth-gate .auth-btn:hover{opacity:.88}
  #auth-gate .auth-error{color:#c0392b;font-size:12px;margin-top:12px;display:none}
  #app-content{display:none}
  .signout-btn{font-family:inherit;font-size:11px;font-weight:700;padding:5px 12px;border-radius:20px;border:1.5px solid rgba(255,255,255,.3);background:none;color:rgba(255,255,255,.8);cursor:pointer;transition:all .15s}
  .signout-btn:hover{background:rgba(255,255,255,.15);color:#fff}

  #auth-gate{position:fixed;inset:0;background:var(--bg);z-index:9999;display:flex;align-items:center;justify-content:center;padding:28px}
  #auth-gate .auth-box{background:#fff;border-radius:18px;padding:38px 46px;text-align:center;box-shadow:0 8px 40px rgba(106,52,96,.15);max-width:390px;width:100%;border:1px solid var(--border)}
  #auth-gate .auth-title{font-size:22px;font-weight:800;color:var(--hp-purple);margin-bottom:8px}
  #auth-gate .auth-sub{font-size:13px;color:var(--muted);margin-bottom:26px;line-height:1.5}
  #auth-gate .auth-btn{width:100%;font-family:inherit;font-size:14px;font-weight:700;padding:13px;border-radius:20px;border:none;background:var(--hp-purple);color:#fff;cursor:pointer;transition:opacity .15s;display:flex;align-items:center;justify-content:center;gap:10px}
  #auth-gate .auth-btn:hover{opacity:.88}
  #auth-gate .auth-error{color:#c0392b;font-size:12px;margin-top:12px;display:none}
  #app-content{display:none}
  .signout-btn{font-family:inherit;font-size:11px;font-weight:700;padding:5px 12px;border-radius:20px;border:1.5px solid rgba(255,255,255,.3);background:none;color:rgba(255,255,255,.8);cursor:pointer;transition:all .15s}
  .signout-btn:hover{background:rgba(255,255,255,.15);color:#fff}
</style>
</head>
<body>

<!-- AUTH GATE -->
<div id="auth-gate">
  <div class="auth-box">
    <div style="font-size:40px;margin-bottom:12px">🏴‍☠️</div>
    <div class="auth-title">Travel Deals</div>
    <div class="auth-sub">Sign in with your HolidayPirates account to continue</div>
    <button class="auth-btn" id="login-btn">
      <svg width="18" height="18" viewBox="0 0 18 18"><path fill="#fff" d="M9 3.48c1.69 0 2.83.73 3.48 1.34l2.54-2.48C13.46.89 11.43 0 9 0 5.48 0 2.44 2.02.96 4.96l2.91 2.26C4.6 5.05 6.62 3.48 9 3.48z"/><path fill="#fff" d="M17.64 9.2c0-.74-.06-1.28-.19-1.84H9v3.34h4.96c-.1.83-.64 2.08-1.84 2.92l2.84 2.2c1.7-1.57 2.68-3.88 2.68-6.62z"/><path fill="#fff" d="M3.88 10.78A5.54 5.54 0 0 1 3.58 9c0-.62.11-1.22.29-1.78L.96 4.96A9.008 9.008 0 0 0 0 9c0 1.45.35 2.82.96 4.04l2.92-2.26z"/><path fill="#fff" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.84-2.2c-.76.53-1.78.9-3.12.9-2.38 0-4.4-1.57-5.12-3.74L.97 13.04C2.45 15.98 5.48 18 9 18z"/></svg>
      Sign in with Google
    </button>
    <div class="auth-error" id="auth-error">Access restricted to HolidayPirates accounts.</div>
  </div>
</div>

<div id="app-content">


<div class="topbar">
  <div class="topbar-brand">
    <svg width="26" height="26" viewBox="0 0 100 100" fill="none"><path d="M50 5C30 5 14 21 14 41c0 28 36 54 36 54s36-26 36-54c0-20-16-36-36-36z" fill="#fff" opacity=".15"/><path d="M50 8C31 8 16 23 16 42c0 27 34 52 34 52s34-25 34-52C84 23 69 8 50 8z" fill="none" stroke="#fff" stroke-width="2" opacity=".3"/><circle cx="62" cy="35" r="14" fill="#e63030"/><circle cx="62" cy="35" r="9" fill="#c0392b"/><circle cx="68" cy="31" r="3" fill="#fff"/><path d="M58 44 L45 55 L52 58 L48 68 L62 56 L55 53 Z" fill="#f39c12"/><path d="M48 25 L52 18 L56 25" fill="#27ae60"/><path d="M54 22 L60 17 L62 24" fill="#2ecc71"/></svg>
    <h1>HolidayPirates · Deal Board</h1>
  </div>
  <div class="topbar-right"><button class="signout-btn" id="signout-btn">Sign out</button><button class="signout-btn" id="signout-btn">Sign out</button>
    <span class="topbar-meta">Updated __GENERATED__ · __TOTAL__ deals</span>
    <div class="view-toggle">
      <button class="view-btn-toggle on" id="btn-grid" onclick="setView('grid')" title="Grid view">⊞</button>
      <button class="view-btn-toggle" id="btn-list" onclick="setView('list')" title="List view">≡</button>
    </div>
  </div>
</div>

<!-- FILTER BAR -->
<div class="filterbar">

  <div class="filter-row">
    <span class="filter-label">Market</span>
    <button class="pill market on" data-group="market" data-val="ES">🇪🇸 ES</button>
    <button class="pill market" data-group="market" data-val="FR">🇫🇷 FR</button>
    <button class="pill market" data-group="market" data-val="IT">🇮🇹 IT</button>
    <div class="search-wrap" style="margin-left:auto">
      <span class="search-icon">🔍</span>
      <input type="text" id="f-search" placeholder="Search hotel, destination…" oninput="applyFilters()">
    </div>
    <select class="hp-select" id="f-sort" onchange="applyFilters()">
      <option value="score">Best value ✦</option>
      <option value="price_asc">Price ↑</option>
      <option value="price_desc">Price ↓</option>
      <option value="night_asc">Price/night ↑</option>
      <option value="stars_desc">Stars ↓</option>
      <option value="drop">Biggest drop</option>
    </select>
    <span class="rc" id="rc"></span>
  </div>

  <div class="filter-row">
    <span class="filter-label">Origin</span>
    <div id="origin-pills" style="display:flex;gap:7px;flex-wrap:wrap"></div>
  </div>

  <div class="filter-row">
    <span class="filter-label">Nights</span>
    <select class="hp-select" id="nights-select" onchange="F.nights=this.value;applyFilters()">
      <option value="">Any</option>
    </select>
    <span style="color:var(--border);margin:0 4px">|</span>
    <span class="filter-label">Type</span>
    <select class="hp-select" id="topic-select" onchange="F.topic=this.value;applyFilters()">
      <option value="">All types</option>
    </select>
    <span style="color:var(--border);margin:0 4px">|</span>
    <span class="filter-label">Price</span>
    <input type="number" id="f-pmin" placeholder="Min €" class="hp-select" style="width:72px" oninput="applyFilters()">
    <span style="color:var(--muted);font-size:13px">–</span>
    <input type="number" id="f-pmax" placeholder="Max €" class="hp-select" style="width:72px" oninput="applyFilters()">
  </div>

  <div class="filter-row">
    <span class="filter-label">Board</span>
    <button class="pill on" data-group="board" data-val="">All</button>
    <div id="board-pills" style="display:flex;gap:7px;flex-wrap:wrap"></div>
    <span style="color:var(--border);margin:0 4px">|</span>
    <span class="filter-label">Stars</span>
    <button class="pill on" data-group="stars" data-val="">All</button>
    <button class="pill" data-group="stars" data-val="3">★★★</button>
    <button class="pill" data-group="stars" data-val="4">★★★★</button>
    <button class="pill" data-group="stars" data-val="5">★★★★★</button>
  </div>

  <div class="filter-row">
    <span class="filter-label">Month</span>
    <div id="month-pills" style="display:flex;gap:7px;flex-wrap:wrap">
      <button class="pill on" data-group="month" data-val="">All</button>
    </div>
  </div>

</div>

<!-- REGION TABS -->
<div class="region-tabs" id="region-tabs"></div>

<!-- CONTENT -->
<div class="grid-wrap">
  <div id="content"></div>
</div>

<script>
const D = __DATA__;

const F = { market:"ES", origin:"", nights:"", board:"", stars:"", topic:"", month:"", region:"All", pmin:0, pmax:Infinity, search:"" };
let filtered = [];
let viewMode = "grid";

window.addEventListener("DOMContentLoaded", () => {
  buildDynamicPills();
  buildRegionTabs();
  bindPills();
  applyFilters();
});

function setView(mode) {
  viewMode = mode;
  document.getElementById("btn-grid").classList.toggle("on", mode==="grid");
  document.getElementById("btn-list").classList.toggle("on", mode==="list");
  render();
}

function buildDynamicPills(market) {
  market = market || F.market || "ES";

  // Origins
  const op = document.getElementById("origin-pills");
  op.innerHTML = "";
  const allO = document.createElement("button");
  allO.className = "pill on"; allO.dataset.group = "origin"; allO.dataset.val = "";
  allO.textContent = "All"; op.appendChild(allO);
  (D.filters.origins_by_market[market] || []).forEach(o => {
    const b = document.createElement("button");
    b.className = "pill"; b.dataset.group = "origin"; b.dataset.val = o.code;
    b.textContent = o.label; op.appendChild(b);
  });

  // Nights
  const nd = document.getElementById("nights-select");
  nd.innerHTML = "<option value=''>Any</option>";
  (D.filters.noches_by_market[market] || []).forEach(n => {
    nd.add(new Option(n + " nights", n));
  });

  // Boards
  const bp = document.getElementById("board-pills");
  bp.innerHTML = "";
  (D.filters.boards_by_market[market] || []).forEach(b => {
    const btn = document.createElement("button");
    btn.className = "pill"; btn.dataset.group = "board"; btn.dataset.val = b;
    btn.textContent = b; bp.appendChild(btn);
  });

  // Topics - dropdown
  const td2 = document.getElementById("topic-select");
  if (td2) {
    td2.innerHTML = "<option value=''>All types</option>";
    const topics = new Set();
    D.products.filter(p => p.market === market).forEach(p => (p.topics||[]).forEach(t => topics.add(t)));
    [...topics].sort().forEach(t => td2.add(new Option(t, t)));
  }

  // Months
  const mp = document.getElementById("month-pills");
  if (mp) {
    mp.innerHTML = '<button class="pill on" data-group="month" data-val="">All</button>';
    const MN = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    (D.filters.months_by_market[market] || []).forEach(m => {
      const [y, mo] = m.split("-");
      const btn = document.createElement("button");
      btn.className = "pill"; btn.dataset.group = "month"; btn.dataset.val = m;
      btn.textContent = MN[parseInt(mo)-1] + " " + y.slice(2); mp.appendChild(btn);
    });
  }
}

function buildRegionTabs() {
  const counts = { All: 0 };
  D.products.filter(p => p.market === F.market).forEach(p => {
    counts.All++;
    const r = p.region_tab || "Other";
    counts[r] = (counts[r]||0) + 1;
  });
  const wrap = document.getElementById("region-tabs");
  wrap.innerHTML = "";
  ["All","Spain","Europe","Caribbean","Middle East & Africa","Asia & Pacific","Americas","Other"].forEach(r => {
    if (!counts[r]) return;
    const b = document.createElement("button");
    b.className = "rtab" + (r===F.region ? " on" : "");
    b.dataset.region = r;
    b.innerHTML = r + `<span class="n">${counts[r]}</span>`;
    b.onclick = () => { F.region=r; document.querySelectorAll(".rtab").forEach(x=>x.classList.toggle("on",x.dataset.region===r)); applyFilters(); };
    wrap.appendChild(b);
  });
}

function bindPills() {
  document.addEventListener("click", e => {
    const pill = e.target.closest(".pill[data-group]");
    if (!pill || pill.disabled) return;
    const group = pill.dataset.group, val = pill.dataset.val;
    document.querySelectorAll(`.pill[data-group="${group}"]`).forEach(p=>p.classList.remove("on"));
    pill.classList.add("on");
    F[group] = val;
    if (group === "market") {
      F.origin=""; F.board=""; F.nights=""; F.topic=""; F.month=""; F.region="All";
      buildDynamicPills(val);
      buildRegionTabs();
    }
    applyFilters();
  });
}

function applyFilters() {
  F.pmin   = parseFloat(document.getElementById("f-pmin")?.value) || 0;
  F.pmax   = parseFloat(document.getElementById("f-pmax")?.value) || Infinity;
  F.search = (document.getElementById("f-search")?.value || "").toLowerCase();
  const sort = document.getElementById("f-sort")?.value || "score";

  const BOARDS = {"All Inclusive":"All Inclusive","Half Board":"Half Board","Full Board":"Full Board","Breakfast":"Breakfast","Room Only":"Room Only","Todo Incluido":"All Inclusive","Media Pensión":"Half Board","Pensión Completa":"Full Board","Desayuno":"Breakfast","Solo Alojamiento":"Room Only","Tout inclus":"All Inclusive","Demi-pension":"Half Board","Pension complète":"Full Board","Petit-déjeuner":"Breakfast","Logement seul":"Room Only","Tutto incluso":"All Inclusive","Mezza pensione":"Half Board","Pensione completa":"Full Board","Prima colazione":"Breakfast","Solo pernottamento":"Room Only","Pensione come da programma":"Full Board","UAI":"All Inclusive","AIL":"All Inclusive","AIS":"All Inclusive","HAI":"All Inclusive","SAI":"All Inclusive","SP":"Half Board","ABF":"Breakfast","CBF":"Breakfast","DB":"Breakfast","UHB":"Half Board","GGBB":"Breakfast"};
  const AIRPORT = {"MAD":"Madrid","BCN":"Barcelona","BIO":"Bilbao","SVQ":"Sevilla","VLC":"Valencia","AGP":"Málaga","ALC":"Alicante","OVD":"Asturias","SCQ":"Santiago","SDR":"Santander","ZAZ":"Zaragoza","GRX":"Granada","PMI":"Mallorca","CDG":"Paris","ORY":"Paris Orly","LYS":"Lyon","MRS":"Marseille","NCE":"Nice","TLS":"Toulouse","BOD":"Bordeaux","NTE":"Nantes","LIL":"Lille","FCO":"Roma","MXP":"Milano","LIN":"Milano Linate","BGY":"Bergamo","VCE":"Venezia","NAP":"Napoli","BLQ":"Bologna","CTA":"Catania","PMO":"Palermo","PAR":"Paris","ROM":"Roma","MIL":"Milano"};

  filtered = [];
  for (const p of D.products) {
    if (F.market && p.market !== F.market) continue;
    if (F.region !== "All" && p.region_tab !== F.region) continue;
    if (F.stars  && String(p.estrellas||"") !== F.stars) continue;
    if (F.topic  && !(p.topics||[]).includes(F.topic)) continue;
    if (F.search) {
      const hay = ((p.nombre||"")+(p.pais||"")+(p.resort||"")+(p.db_region||"")).toLowerCase();
      if (!hay.includes(F.search)) continue;
    }

    let candidates = p.prices || [];
    if (F.origin) candidates = candidates.filter(pr => pr.o === F.origin);
    if (F.board)  candidates = candidates.filter(pr => { const b = pr.b || (pr.td&&pr.td[0]&&pr.td[0].b)||""; return (BOARDS[b]||b) === F.board; });
    if (F.nights) candidates = candidates.filter(pr => String(pr.n) === String(F.nights));
    if (F.month)  candidates = candidates.filter(pr => (pr.td||[]).some(td => td.d && td.d.startsWith(F.month)));
    if (!candidates.length) continue;

    let best;
    if (F.month) {
      let bestDate = null;
      for (const pr of candidates) {
        for (const td of (pr.td||[])) {
          if (td.d && td.d.startsWith(F.month) && (!bestDate || td.p < bestDate.p))
            bestDate = {...td, _pr: pr};
        }
      }
      if (!bestDate) continue;
      best = {...bestDate._pr, p: bestDate.p, _date: bestDate.d, _return: bestDate.r};
    } else {
      best = candidates.reduce((a,b) => a.p < b.p ? a : b);
    }
    if (best.p < F.pmin || best.p > F.pmax) continue;

    filtered.push({...p,
      _precio:       best.p,
      _origen:       best.o,
      _origen_lbl:   AIRPORT[best.o] || best.o,
      _noches:       best.n,
      _pension:      BOARDS[best.b] || best.b,
      _precio_ant:   best.pa,
      _precio_noche: best.n ? Math.round(best.p / best.n) : null,
      _bajada:       best.pa && best.p < best.pa ? Math.round((best.pa-best.p)/best.pa*100) : null,
      _date:         best._date || null,
      _return:       best._return || null,
    });
  }

  if (sort==="score")      filtered.sort((a,b)=>(b.score||0)-(a.score||0));
  if (sort==="price_asc")  filtered.sort((a,b)=>((a._precio||a.precio_actual)||9999)-((b._precio||b.precio_actual)||9999));
  if (sort==="price_desc") filtered.sort((a,b)=>((b._precio||b.precio_actual)||0)-((a._precio||a.precio_actual)||0));
  if (sort==="night_asc")  filtered.sort((a,b)=>((a._precio_noche||a.precio_noche)||9999)-((b._precio_noche||b.precio_noche)||9999));
  if (sort==="stars_desc") filtered.sort((a,b)=>(b.estrellas||0)-(a.estrellas||0));
  if (sort==="drop")       filtered.sort((a,b)=>((b._bajada||b.bajada_pct)||0)-((a._bajada||a.bajada_pct)||0));

  document.getElementById("rc").textContent = filtered.length + " result" + (filtered.length===1?"":"s");
  render();
}

function render() {
  const el = document.getElementById("content");
  if (!filtered.length) {
    el.innerHTML = '<div class="empty"><div class="icon">🏖️</div><p>No results found.</p></div>';
    return;
  }
  el.innerHTML = "";
  if (viewMode === "grid") {
    const grid = document.createElement("div"); grid.className = "grid";
    filtered.forEach(p => grid.appendChild(makeCard(p)));
    el.appendChild(grid);
  } else {
    const list = document.createElement("div"); list.className = "list";
    filtered.forEach(p => list.appendChild(makeRow(p)));
    el.appendChild(list);
  }
}

function scoreClass(s){ return s>=70?"s-hi":s>=40?"s-mid":"s-lo"; }

function makeCard(p) {
  const el = document.createElement("div"); el.className = "card";
  const precio    = p._precio ?? p.precio_actual;
  const origenLbl = p._origen_lbl ?? p.origen_label ?? "";
  const noches    = p._noches ?? p.mejor_noches;
  const pNoche    = p._precio_noche ?? p.precio_noche;
  const pension   = p._pension ?? p.pension_en ?? "";
  const precioAnt = p._precio_ant ?? p.precio_anterior;
  const bajada    = p._bajada ?? p.bajada_pct;
  const stars     = p.estrellas ? "★".repeat(parseInt(p.estrellas)) : "";
  const ta        = p.tripadvisor_rating ? `<span class="bdg bdg-ta">⭐ ${p.tripadvisor_rating}${p.tripadvisor_reviews?" ("+p.tripadvisor_reviews+")":""}</span>` : "";
  const board     = pension ? `<span class="bdg bdg-board">${esc(pension)}</span>` : "";
  const starsB    = stars ? `<span class="bdg bdg-stars">${stars}</span>` : "";
  const loc       = [p.resort, p.pais].filter(Boolean).join(", ");
  const from      = origenLbl ? `From ${esc(origenLbl)}` : "";
  const nightStr  = [pNoche?Math.round(pNoche)+"€/night":"", noches?noches+"n":""].filter(Boolean).join(" · ");
  const dateStr   = p._date ? `✈ ${p._date}${p._return?" → "+p._return:""}` : "";
  const img       = p.foto_url ? `<img src="${esc(p.foto_url)}" loading="lazy" alt="" onerror="this.parentElement.innerHTML='<div class=no-img>🏨</div>'">` : `<div class="no-img">🏨</div>`;

  el.innerHTML = `
    <div class="card-img">
      ${img}
      <div class="score-pill"><span class="sdot ${scoreClass(p.score||0)}"></span>${p.score||0}</div>
      ${bajada>0?`<div class="drop-pill">↓ ${bajada}%</div>`:""}
    </div>
    <div class="card-body">
      <div class="card-name">${esc(p.nombre||"")}</div>
      ${loc?`<div class="card-loc">📍 ${esc(loc)}</div>`:""}
      <div class="card-badges">${starsB}${board}${ta}</div>
      ${dateStr?`<div style="font-size:11px;color:var(--hp-purple);margin-top:3px;font-weight:600">${esc(dateStr)}</div>`:""}
    </div>
    <div class="card-footer">
      <div>
        <div class="price-from">${from}</div>
        <div class="price-main">${precio?Math.round(precio)+"€":"—"}</div>
        <div class="price-sub">${nightStr}</div>
        ${bajada>0&&precioAnt?`<div class="price-old">${Math.round(precioAnt)}€</div>`:""}
      </div>
      <a href="${esc(p.url)}" target="_blank" class="cta-btn">View →</a>
    </div>`;
  return el;
}

function makeRow(p) {
  const el = document.createElement("div"); el.className = "list-item";
  const precio    = p._precio ?? p.precio_actual;
  const origenLbl = p._origen_lbl ?? p.origen_label ?? "";
  const noches    = p._noches ?? p.mejor_noches;
  const pNoche    = p._precio_noche ?? p.precio_noche;
  const pension   = p._pension ?? p.pension_en ?? "";
  const precioAnt = p._precio_ant ?? p.precio_anterior;
  const bajada    = p._bajada ?? p.bajada_pct;
  const stars     = p.estrellas ? "★".repeat(parseInt(p.estrellas)) : "";
  const ta        = p.tripadvisor_rating ? `<span class="bdg bdg-ta" style="font-size:10px;padding:1px 6px">⭐ ${p.tripadvisor_rating}</span>` : "";
  const board     = pension ? `<span class="bdg bdg-board" style="font-size:10px;padding:1px 6px">${esc(pension)}</span>` : "";
  const starsB    = stars ? `<span class="bdg bdg-stars" style="font-size:10px;padding:1px 6px">${stars}</span>` : "";
  const loc       = [p.resort, p.pais].filter(Boolean).join(", ");
  const from      = origenLbl ? `From ${esc(origenLbl)}` : "";
  const nightStr  = [pNoche?Math.round(pNoche)+"€/night":"", noches?noches+"n":""].filter(Boolean).join(" · ");
  const dateStr   = p._date ? `✈ ${p._date}${p._return?" → "+p._return:""}` : "";
  const img       = p.foto_url ? `<img src="${esc(p.foto_url)}" loading="lazy" alt="" onerror="this.parentElement.innerHTML='<div class=no-img style=height:80px>🏨</div>'">` : `<div class="no-img" style="height:80px">🏨</div>`;

  el.innerHTML = `
    <div class="list-thumb">
      ${img}
      <div class="list-score"><span class="sdot ${scoreClass(p.score||0)}" style="width:5px;height:5px"></span>${p.score||0}</div>
    </div>
    <div class="list-body">
      <div class="list-name">${esc(p.nombre||"")}</div>
      ${loc?`<div class="list-loc">📍 ${esc(loc)}</div>`:""}
      <div class="list-badges">${starsB}${board}${ta}</div>
    </div>
    <div class="list-right">
      ${bajada>0?`<div class="list-drop">↓ ${bajada}%</div>`:""}
      <div class="price-from" style="text-align:right">${from}</div>
      <div class="price-main" style="font-size:20px">${precio?Math.round(precio)+"€":"—"}</div>
      <div class="price-sub" style="text-align:right">${nightStr}</div>
      ${bajada>0&&precioAnt?`<div class="price-old">${Math.round(precioAnt)}€</div>`:""}
      <a href="${esc(p.url)}" target="_blank" class="cta-btn" style="margin-top:4px;font-size:11px;padding:5px 10px">View →</a>
    </div>`;
  return el;
}

function esc(s){ return String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }
</script>
</div><!-- /app-content -->


</div><!-- /app-content -->

<!-- AUTH — redirect flow -->
<script>
  const IDENTITY = "https://perfectstay-hp.netlify.app/.netlify/identity";
  const SITE_ID  = "2a8514a9-b44a-4909-b50e-7538f8133d2c";
  const gate       = document.getElementById('auth-gate');
  const appDiv     = document.getElementById('app-content');
  const loginBtn   = document.getElementById('login-btn');
  const errMsg     = document.getElementById('auth-error');
  const signoutBtn = document.getElementById('signout-btn');

  function isAllowed(email) {
    return email.endsWith('@holidaypirates.com') || email.endsWith('@extern.holidaypirates.com');
  }

  function showApp(email) {
    gate.style.display   = 'none';
    appDiv.style.display = 'block';
  }

  function handleCallback() {
    const hash = window.location.hash;
    if (!hash.includes('access_token')) return false;
    const params = new URLSearchParams(hash.slice(1));
    const token  = params.get('access_token');
    if (!token) return false;
    fetch(IDENTITY + '/user', { headers: { Authorization: 'Bearer ' + token } })
      .then(r => r.json())
      .then(user => {
        const email = (user.email || '').toLowerCase();
        if (isAllowed(email)) {
          localStorage.setItem('hp_token', token);
          localStorage.setItem('hp_email', email);
          window.location.hash = '';
          showApp(email);
        } else {
          errMsg.textContent = 'Access restricted to HolidayPirates accounts.';
          errMsg.style.display = 'block';
          localStorage.removeItem('hp_token');
          localStorage.removeItem('hp_email');
        }
      })
      .catch(() => { errMsg.textContent = 'Login failed.'; errMsg.style.display = 'block'; });
    return true;
  }

  function checkSession() {
    const token = localStorage.getItem('hp_token');
    const email = localStorage.getItem('hp_email');
    if (!token || !email) return false;
    fetch(IDENTITY + '/user', { headers: { Authorization: 'Bearer ' + token } })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(user => {
        const realEmail = (user.email || '').toLowerCase();
        if (isAllowed(realEmail)) showApp(realEmail);
        else { localStorage.removeItem('hp_token'); localStorage.removeItem('hp_email'); }
      })
      .catch(() => { localStorage.removeItem('hp_token'); localStorage.removeItem('hp_email'); });
    return true;
  }

  window.addEventListener('DOMContentLoaded', () => {
    if (!handleCallback()) checkSession();
  });

  loginBtn.addEventListener('click', () => {
    errMsg.style.display = 'none';
    window.location.href = IDENTITY + '/authorize?provider=google&site_id=' + SITE_ID;
  });

  if (signoutBtn) signoutBtn.addEventListener('click', () => {
    localStorage.removeItem('hp_token');
    localStorage.removeItem('hp_email');
    location.reload();
  });
</script>
</body>
</html>"""


if __name__ == "__main__":
    build()
