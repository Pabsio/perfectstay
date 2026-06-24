"""
scraper.py — PerfectStay multi-mercado (ES, FR, IT)
Guarda precio mínimo por combo (producto × origen × noches).

Uso:
    python3 scraper.py                   # todos los mercados
    python3 scraper.py --market ES       # solo España
    python3 scraper.py --market FR,IT    # Francia e Italia
    python3 scraper.py --dry-run         # sin guardar
    python3 scraper.py --workers 10      # menos hilos
"""

import time, json, argparse
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from database import init_db, upsert_producto, replace_precios, mark_inactive, PENSION_MAP

MARKETS = {
    "ES": {"base": "https://holidaypirates.perfectstay.com/current/es-ES", "shop": "HPHOESES", "lang": "es-ES", "url_prefix": "es-ES"},
    "FR": {"base": "https://holidaypirates.perfectstay.com/current/fr-FR", "shop": "HPFR",    "lang": "fr-FR", "url_prefix": "fr-FR"},
    "IT": {"base": "https://holidaypirates.perfectstay.com/current/it-IT", "shop": "HPIT",    "lang": "it-IT", "url_prefix": "it-IT"},
}

TIMEOUT = 15
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def get(url: str, retries=3):
    for i in range(retries):
        try:
            r = SESSION.get(url, timeout=TIMEOUT)
            if r.status_code == 200:
                return r.json()
            return None
        except Exception:
            if i < retries - 1:
                time.sleep(0.5)
    return None


def ts_to_date(ms) -> str:
    if not ms:
        return ""
    try:
        return datetime.fromtimestamp(int(ms)/1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return ""


def fetch_products(market: str) -> list:
    cfg  = MARKETS[market]
    url  = f"{cfg['base']}/{cfg['shop']}/products.json"
    data = get(url)
    if not data:
        print(f"   ❌ No se pudo obtener products.json para {market}")
        return []
    products = data.get("products", data) if isinstance(data, dict) else data
    print(f"   → {len(products)} productos [{market}]")
    return products


def _fetch_detail(args):
    uri, base = args
    if not uri:
        return uri, None
    return uri, get(f"{base}/{uri}.json")


def fetch_all_details(products: list, base: str, workers=20) -> dict:
    details = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(_fetch_detail, (p.get("uri",""), base)): p for p in products}
        for future in as_completed(futures):
            uri, result = future.result()
            if result:
                details[uri] = result
    return details


def extract_city_uris(details: dict) -> set:
    uris = set()
    for detail in details.values():
        for offer in (detail.get("offers") or []):
            for city in (offer.get("pricing") or {}).get("departureCities") or []:
                uri = city.get("uri", "")
                if uri and not uri.endswith("-ZZZ"):
                    uris.add(uri)
    return uris


def _fetch_city(args):
    uri, base = args
    return uri, get(f"{base}/{uri}.json")


def fetch_all_city_prices(city_uris: set, base: str, workers=20) -> dict:
    city_data = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(_fetch_city, (uri, base)): uri for uri in city_uris}
        done = 0
        for future in as_completed(futures):
            done += 1
            uri, data = future.result()
            if data:
                city_data[uri] = data
            if done % 500 == 0:
                print(f"   {done}/{len(city_uris)} prices…")
    return city_data


def parse_min_prices(city_json) -> dict:
    """
    Devuelve {noches: {precio, pension, top_dates}}
    top_dates = lista de las 3 fechas más baratas: [{d, p, r}]
    """
    # Acumular todos los precios por noches
    all_prices = {}  # {noches: [{p, d, r}]}

    if not city_json:
        return {}
    packages = city_json if isinstance(city_json, list) else None
    if packages is None and isinstance(city_json, dict):
        for key in ("packages","offers","departures","results","data","items"):
            if key in city_json and isinstance(city_json[key], list):
                packages = city_json[key]; break
        if packages is None:
            packages = [city_json]

    pension_by_noches = {}

    for pkg in (packages or []):
        if not isinstance(pkg, dict):
            continue
        if "prices" in pkg and isinstance(pkg["prices"], list):
            noches = pkg.get("value")
            if not noches: continue
            noches = int(noches)
            for p in pkg["prices"]:
                if not p.get("o", True): continue
                precio = p.get("p")
                if not precio: continue
                b = p.get("b","")  # b is on each price, not the block
                mapped_b = PENSION_MAP.get(b, b)
                if mapped_b: pension_by_noches[noches] = mapped_b
                all_prices.setdefault(noches, []).append({
                    "p": float(precio),
                    "d": ts_to_date(p.get("dd")),
                    "r": ts_to_date(p.get("ed")),
                    "b": mapped_b,
                })
            continue
        precio = pkg.get("p") or pkg.get("price") or pkg.get("pricePerPerson")
        noches = pkg.get("n") or pkg.get("nights") or pkg.get("value") or pkg.get("numberOfNights")
        if precio and noches:
            precio, noches = float(precio), int(noches)
            dd = pkg.get("dd") or pkg.get("departureDate")
            b  = pkg.get("b","")
            pension_by_noches[noches] = PENSION_MAP.get(b, b)
            all_prices.setdefault(noches, []).append({
                "p": precio,
                "d": ts_to_date(dd) if isinstance(dd,(int,float)) else str(dd or ""),
                "r": ts_to_date(pkg.get("ed")),
                "b": PENSION_MAP.get(b, b),
            })

    # Para cada número de noches, calcular mínimo y top 3 fechas
    result = {}
    for noches, prices in all_prices.items():
        sorted_prices = sorted(prices, key=lambda x: x["p"])
        min_price     = sorted_prices[0]["p"]
        top_dates     = sorted_prices[:3]  # top 3 más baratas
        pension       = pension_by_noches.get(noches, "")
        # Also try to get pension from the price entries themselves
        if not pension and top_dates:
            pension = top_dates[0].get("b", "")
        result[noches] = {
            "precio":    min_price,
            "pension":   pension,
            "top_dates": top_dates,
        }
    return result


def build_min_price_rows(products, details, city_data, market) -> list[dict]:
    mins = {}
    cfg  = MARKETS[market]
    for product in products:
        uri    = product.get("uri","")
        pid    = f"{market}_{product.get('id','')}"
        detail = details.get(uri) or {}
        has    = False
        for offer in (detail.get("offers") or []):
            for city in (offer.get("pricing") or {}).get("departureCities") or []:
                city_uri  = city.get("uri","")
                city_code = city.get("code","")
                if city_uri.endswith("-ZZZ") or not city_uri: continue
                for noches, data in parse_min_prices(city_data.get(city_uri)).items():
                    key = (pid, city_code, noches)
                    if key not in mins or data["precio"] < mins[key]["precio"]:
                        mins[key] = data; has = True
        if not has:
            fpt = product.get("fromPriceType") or {}
            if fpt.get("value") and fpt.get("numberOfNights"):
                key = (pid, "", int(fpt["numberOfNights"]))
                dd  = fpt.get("departureDate")
                mins[key] = {
                    "precio":    float(fpt["value"]),
                    "pension":   fpt.get("mealBasis",""),
                    "top_dates": [{"p": float(fpt["value"]),
                                   "d": ts_to_date(dd) if dd else "",
                                   "r": ""}],
                }
    rows = []
    for (pid, iata, noches), data in mins.items():
        rows.append({
            "producto_id": pid,
            "origen_iata": iata,
            "noches":      noches,
            "precio":      data["precio"],
            "pension":     data["pension"],
            "top_dates":   data.get("top_dates", []),
        })
    return rows


def normalize_product(product: dict, market: str) -> dict:
    cfg    = MARKETS[market]
    fpt    = product.get("fromPriceType") or {}
    ta     = product.get("tripadvisor") or {}
    fotos  = product.get("photos") or []
    gps    = product.get("gps") or {}
    geo    = product.get("geography") or {}
    return {
        "id":                   f"{market}_{product.get('id','')}",
        "uri":                  product.get("uri",""),
        "nombre":               product.get("name",""),
        "pais":                 product.get("country",""),
        "region":               product.get("region",""),
        "resort":               product.get("resort",""),
        "estrellas":            int(product.get("category") or 0),
        "tipo":                 product.get("productExperience","Hotel"),
        "latitud":              gps.get("lat"),
        "longitud":             gps.get("lon"),
        "iata_destino":         geo.get("destinationAirportIATA",""),
        "tripadvisor_rating":   ta.get("rating"),
        "tripadvisor_reviews":  ta.get("reviewsCount"),
        "foto_url":             (fotos[0].get("url") if fotos else None),
        "topics":               json.dumps(product.get("topics") or [], ensure_ascii=False),
        "meses":                json.dumps([m.get("label") for m in (product.get("months") or [])], ensure_ascii=False),
        "precio_ref":           float(fpt["value"]) if fpt.get("value") else None,
        "origen_ref":           fpt.get("departureCity",""),
        "noches_ref":           fpt.get("numberOfNights"),
        "pension_ref":          fpt.get("mealBasis",""),
        "market":               market,
        "url_prefix":           cfg["url_prefix"],
    }


def scrape_market(market: str, workers=20, dry_run=False):
    cfg = MARKETS[market]
    print(f"\n▶ {market}")

    products = fetch_products(market)
    if not products:
        return

    print(f"   Descargando detalles…")
    details   = fetch_all_details(products, cfg["base"], workers)
    city_uris = extract_city_uris(details)
    print(f"   → {len(city_uris)} combos ciudad/producto")

    print(f"   Descargando precios…")
    city_data = fetch_all_city_prices(city_uris, cfg["base"], workers)

    print(f"   Calculando mínimos…")
    rows = build_min_price_rows(products, details, city_data, market)
    print(f"   → {len(rows)} combos precio mínimo")

    if dry_run:
        prices = [r["precio"] for r in rows]
        if prices:
            print(f"   Mín:{min(prices):.0f}€  Máx:{max(prices):.0f}€  Media:{sum(prices)/len(prices):.0f}€")
        return

    active_ids = set()
    for p in products:
        norm = normalize_product(p, market)
        upsert_producto(norm)
        active_ids.add(norm["id"])
    mark_inactive(active_ids, market)

    stats = replace_precios(rows, market)
    print(f"   ✅ Precios: {stats['total']} | ↓ {stats['down']} | ↑ {stats['up']}")


def run(markets=None, workers=20, dry_run=False):
    print(f"\n{'='*60}")
    print(f"  PerfectStay Scraper — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")

    if not dry_run:
        init_db()

    t0 = time.time()
    for market in (markets or list(MARKETS.keys())):
        scrape_market(market, workers=workers, dry_run=dry_run)

    print(f"\n✅ Done in {time.time()-t0:.1f}s\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--market",   type=str, help="ES,FR,IT (comma separated)")
    parser.add_argument("--workers",  type=int, default=20)
    parser.add_argument("--dry-run",  action="store_true")
    args = parser.parse_args()
    markets = [m.strip().upper() for m in args.market.split(",")] if args.market else None
    run(markets=markets, workers=args.workers, dry_run=args.dry_run)
