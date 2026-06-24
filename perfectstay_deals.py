"""
ViajerosPiratas – PerfectStay scraper completo
Extrae TODAS las combinaciones: producto × ciudad de salida × número de noches

Uso:
    pip install requests
    python3 perfectstay_deals.py              # solo stats en pantalla
    python3 perfectstay_deals.py --csv        # exporta deals_{timestamp}.csv
    python3 perfectstay_deals.py --csv --origin Madrid
    python3 perfectstay_deals.py --csv --country Japón --max-price 2000
    python3 perfectstay_deals.py --csv --nights 7
"""

import requests
import csv
import argparse
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

BASE_LIST   = "https://holidaypirates.perfectstay.com/current/es-ES/HPHOESES"
BASE_DETAIL = "https://holidaypirates.perfectstay.com/current/es-ES"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://holidaypirates.perfectstay.com/es-ES",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# ─── helpers ──────────────────────────────────────────────────────────────────

def get(url, retries=3):
    for i in range(retries):
        try:
            r = SESSION.get(url, timeout=15)
            if r.status_code == 200:
                return r.json()
            return None
        except Exception:
            if i < retries - 1:
                time.sleep(0.5)
    return None


def ts(ms):
    if not ms:
        return ""
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return ""


# ─── nivel 1: lista de productos ──────────────────────────────────────────────

def fetch_product_list():
    print("📥 Descargando lista de productos...")
    data = get(f"{BASE_LIST}/products.json")
    if not data:
        raise SystemExit("❌ Error al obtener products.json")
    products = data.get("products", data) if isinstance(data, dict) else data
    print(f"   ✓ {len(products)} productos")
    return products


# ─── nivel 2: detalle de cada producto ────────────────────────────────────────

def fetch_product_detail(product):
    uri = product.get("uri", "")
    if not uri:
        return uri, None
    # URL SIN HPHOESES
    data = get(f"{BASE_DETAIL}/{uri}.json")
    return uri, data


def fetch_all_details(products, workers=20):
    print(f"📥 Descargando detalles ({len(products)} productos, {workers} hilos)...")
    details = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(fetch_product_detail, p): p for p in products}
        done = 0
        for future in as_completed(futures):
            done += 1
            uri, result = future.result()
            if result:
                details[uri] = result
            if done % 50 == 0:
                print(f"   {done}/{len(products)}...")
    print(f"   ✓ {len(details)} detalles obtenidos")
    return details


# ─── nivel 3: precios por ciudad × duración ───────────────────────────────────

def fetch_city_prices(sale_uri):
    # URL SIN HPHOESES
    data = get(f"{BASE_DETAIL}/{sale_uri}.json")
    return sale_uri, data


def fetch_all_city_prices(city_uris, workers=30):
    print(f"📥 Descargando precios ({len(city_uris)} combos ciudad/producto, {workers} hilos)...")
    city_data = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(fetch_city_prices, uri): uri for uri in city_uris}
        done = 0
        for future in as_completed(futures):
            done += 1
            uri, data = future.result()
            if data:
                city_data[uri] = data
            if done % 100 == 0:
                print(f"   {done}/{len(city_uris)}...")
    print(f"   ✓ {len(city_data)} respuestas obtenidas")
    return city_data


# ─── extracción de URIs de ciudad ─────────────────────────────────────────────

def extract_city_uris(details):
    uris = set()
    for detail in details.values():
        for offer in (detail.get("offers") or []):
            pricing = offer.get("pricing") or {}
            for city in (pricing.get("departureCities") or []):
                city_uri = city.get("uri", "")
                if city_uri and not city_uri.endswith("-ZZZ"):
                    uris.add(city_uri)
    return uris


# ─── parseo del JSON de ciudad ────────────────────────────────────────────────

def parse_city_json(city_json):
    """
    Extrae lista de {nights, price_eur, departure_date, return_date, meal_basis}
    del JSON de s{saleId}-{IATA}.json
    """
    rows = []
    if not city_json:
        return rows

    packages = None
    if isinstance(city_json, list):
        packages = city_json
    elif isinstance(city_json, dict):
        for key in ("packages", "offers", "departures", "results", "data", "items"):
            if key in city_json and isinstance(city_json[key], list):
                packages = city_json[key]
                break
        if packages is None:
            packages = [city_json]

    if not packages:
        return rows

    for pkg in packages:
        if not isinstance(pkg, dict):
            continue

        price = pkg.get("p") or pkg.get("price") or pkg.get("pricePerPerson")
        if price is None:
            for k in ("from", "minPrice", "pricing"):
                nested = pkg.get(k)
                if isinstance(nested, dict):
                    price = nested.get("p") or nested.get("price")
                    break

        nights = (pkg.get("n") or pkg.get("nights") or
                  pkg.get("duration") or pkg.get("numberOfNights"))

        dd_raw = pkg.get("dd") or pkg.get("departureDate") or pkg.get("startDate")
        ed_raw = pkg.get("ed") or pkg.get("returnDate") or pkg.get("endDate")

        dep_date = ts(dd_raw) if isinstance(dd_raw, (int, float)) else str(dd_raw or "")
        ret_date = ts(ed_raw) if isinstance(ed_raw, (int, float)) else str(ed_raw or "")

        meal = pkg.get("b") or pkg.get("mealBasis") or pkg.get("board") or ""

        if price and nights:
            rows.append({
                "nights":         int(nights),
                "price_eur":      float(price),
                "departure_date": dep_date,
                "return_date":    ret_date,
                "meal_basis":     meal,
            })

    return rows


# ─── construcción de la tabla plana ───────────────────────────────────────────

def build_rows(products, details, city_data):
    rows = []

    for product in products:
        uri    = product.get("uri", "")
        detail = details.get(uri) or {}

        base = {
            "product_id":   product.get("id") or detail.get("id"),
            "name":         product.get("name") or detail.get("name"),
            "stars":        product.get("category") or detail.get("category"),
            "experience":   product.get("productExperience") or detail.get("productExperience"),
            "country":      product.get("country") or detail.get("country"),
            "region":       product.get("region") or detail.get("region"),
            "resort":       product.get("resort") or detail.get("resort"),
            "with_flight":  product.get("includeOfferWithFlight"),
            "is_flashsale": product.get("isFlashsale"),
            "product_url":  f"https://holidaypirates.perfectstay.com/es-ES/product/{uri}",
            "image_url":    (product.get("photos") or [{}])[0].get("url", ""),
        }

        has_rows = False

        for offer in (detail.get("offers") or []):
            pricing   = offer.get("pricing") or {}
            cities    = pricing.get("departureCities") or []

            for city in cities:
                city_uri   = city.get("uri", "")
                city_code  = city.get("code", "")
                city_label = city.get("label", "")

                if city_uri.endswith("-ZZZ") or not city_uri:
                    continue

                cdata     = city_data.get(city_uri)
                pr_rows   = parse_city_json(cdata)

                if pr_rows:
                    has_rows = True
                    for pr in pr_rows:
                        rows.append({**base,
                            "city_code":      city_code,
                            "city_label":     city_label,
                            "nights":         pr["nights"],
                            "price_eur":      pr["price_eur"],
                            "departure_date": pr["departure_date"],
                            "return_date":    pr["return_date"],
                            "meal_basis":     pr["meal_basis"],
                        })
                else:
                    # fallback: precio mínimo del nivel 2
                    city_from = city.get("from") or {}
                    price     = city_from.get("p")
                    if price:
                        has_rows = True
                        rows.append({**base,
                            "city_code":      city_code,
                            "city_label":     city_label,
                            "nights":         city_from.get("n"),
                            "price_eur":      float(price),
                            "departure_date": ts(city_from.get("dd")),
                            "return_date":    ts(city_from.get("ed")),
                            "meal_basis":     city_from.get("b", ""),
                        })

        # fallback final: fromPriceType de products.json
        if not has_rows:
            fpt       = product.get("fromPriceType") or {}
            price_raw = fpt.get("value")
            if price_raw:
                rows.append({**base,
                    "city_code":      "",
                    "city_label":     fpt.get("departureCity", ""),
                    "nights":         fpt.get("numberOfNights"),
                    "price_eur":      float(price_raw),
                    "departure_date": ts(fpt.get("departureDate")),
                    "return_date":    "",
                    "meal_basis":     fpt.get("mealBasis", ""),
                })

    return rows


# ─── filtros ──────────────────────────────────────────────────────────────────

def filter_rows(rows, min_price=None, max_price=None, origin=None, country=None, nights=None):
    if min_price:
        rows = [r for r in rows if r["price_eur"] >= min_price]
    if max_price:
        rows = [r for r in rows if r["price_eur"] <= max_price]
    if origin:
        rows = [r for r in rows if origin.lower() in
                (r["city_label"] or r["city_code"]).lower()]
    if country:
        rows = [r for r in rows if country.lower() in (r["country"] or "").lower()]
    if nights:
        rows = [r for r in rows if r["nights"] == nights]
    return rows


# ─── stats ────────────────────────────────────────────────────────────────────

def print_stats(rows):
    if not rows:
        print("Sin resultados.")
        return
    prices = [r["price_eur"] for r in rows]
    print(f"\n{'='*65}")
    print(f"  {len(rows)} combinaciones  |  "
          f"min €{min(prices):.0f}  ·  max €{max(prices):.0f}  ·  "
          f"media €{sum(prices)/len(prices):.0f}")

    top = sorted(rows, key=lambda r: r["price_eur"])[:10]
    print("\n🏆  Top 10 más baratos:")
    for r in top:
        print(f"    €{r['price_eur']:.0f}  {r['nights']}n  "
              f"{(r['city_label'] or r['city_code']):12}  →  "
              f"{(r['resort'] or r['country'] or ''):22}  {r['name'][:35]}")

    print("\n🌍  Por país:")
    for country, count in Counter(r["country"] for r in rows).most_common(12):
        pc = [r["price_eur"] for r in rows if r["country"] == country]
        print(f"    {count:4d}  {country:25}  desde €{min(pc):.0f}")

    print("\n✈️   Por ciudad de salida:")
    for city, count in Counter(
            r["city_label"] or r["city_code"] for r in rows).most_common(10):
        pc = [r["price_eur"] for r in rows
              if (r["city_label"] or r["city_code"]) == city]
        print(f"    {count:4d}  {city:15}  desde €{min(pc):.0f}")


# ─── CSV ──────────────────────────────────────────────────────────────────────

def export_csv(rows, path):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n✓ CSV guardado: {path}  ({len(rows)} filas)")


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ViajerosPiratas PerfectStay – scraper completo")
    parser.add_argument("--csv",       action="store_true")
    parser.add_argument("--min-price", type=float, default=None)
    parser.add_argument("--max-price", type=float, default=None)
    parser.add_argument("--origin",    type=str,   default=None,
                        help="Ciudad salida: Madrid, Barcelona, Sevilla...")
    parser.add_argument("--country",   type=str,   default=None,
                        help="País destino: México, Japón, Sri Lanka...")
    parser.add_argument("--nights",    type=int,   default=None,
                        help="Exactamente N noches")
    parser.add_argument("--workers",   type=int,   default=20,
                        help="Hilos concurrentes (default 20)")
    args = parser.parse_args()

    t0 = time.time()

    products   = fetch_product_list()
    details    = fetch_all_details(products, workers=args.workers)
    city_uris  = extract_city_uris(details)
    print(f"   → {len(city_uris)} combinaciones producto×ciudad detectadas")
    city_data  = fetch_all_city_prices(city_uris, workers=args.workers)

    print("🔧 Procesando datos...")
    rows = build_rows(products, details, city_data)
    print(f"   ✓ {len(rows)} filas generadas")

    rows = filter_rows(rows, args.min_price, args.max_price,
                       args.origin, args.country, args.nights)
    if any([args.min_price, args.max_price, args.origin, args.country, args.nights]):
        print(f"   → {len(rows)} filas tras filtros")

    print_stats(rows)

    if args.csv:
        ts_str = datetime.now().strftime("%Y%m%d_%H%M")
        export_csv(rows, f"deals_{ts_str}.csv")

    print(f"\n⏱️  Completado en {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
