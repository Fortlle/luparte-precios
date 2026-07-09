"""
Scraper Walmart.com.mx
Método: curl_cffi (TLS fingerprint Chrome) + extracción de __NEXT_DATA__ JSON
Sin proxies, sin JavaScript, sin Playwright.
Cubre: Walmart, Bodega Aurrerá, Sam's Club (mismo grupo)
"""

import json
import time
import random
from curl_cffi import requests
from parsel import Selector
from utils import insertar_producto

# Categorías a scrapear con sus URLs de búsqueda
# Cada una tiene su cadena y URL de listado
TARGETS = [
    # (cadena, url_busqueda, categoria, subcategoria)
    ("Walmart", "https://www.walmart.com.mx/grocery/lacteos", "Lácteos", "General"),
    ("Walmart", "https://www.walmart.com.mx/grocery/frutas-y-verduras", "Frutas y Verduras", "General"),
    ("Walmart", "https://www.walmart.com.mx/grocery/carnes-y-mariscos", "Carnes", "General"),
    ("Walmart", "https://www.walmart.com.mx/grocery/abarrotes", "Abarrotes", "General"),
    ("Walmart", "https://www.walmart.com.mx/grocery/bebidas", "Bebidas", "General"),
    ("Walmart", "https://www.walmart.com.mx/grocery/limpieza-del-hogar", "Limpieza", "Hogar"),
    ("Walmart", "https://www.walmart.com.mx/grocery/cuidado-personal", "Salud", "Cuidado personal"),
    ("Walmart", "https://www.walmart.com.mx/farmacias", "Salud", "Medicamentos"),
    ("Walmart", "https://www.walmart.com.mx/electronica", "Electrónica", "General"),
    ("Bodega Aurrerá", "https://www.bodegaaurrera.com.mx/grocery/lacteos", "Lácteos", "General"),
    ("Bodega Aurrerá", "https://www.bodegaaurrera.com.mx/grocery/frutas-y-verduras", "Frutas y Verduras", "General"),
    ("Bodega Aurrerá", "https://www.bodegaaurrera.com.mx/grocery/abarrotes", "Abarrotes", "General"),
    ("Sam's Club", "https://www.sams.com.mx/productos/despensa", "Abarrotes", "General"),
    ("Sam's Club", "https://www.sams.com.mx/productos/electronicos", "Electrónica", "General"),
]

HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "accept-language": "es-MX,es;q=0.9,en;q=0.8",
    "accept-encoding": "gzip, deflate, br",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}


def extraer_productos_next_data(html: str, cadena: str, categoria: str, subcategoria: str) -> int:
    """Extrae productos del JSON __NEXT_DATA__ embebido en el HTML."""
    sel = Selector(text=html)
    next_data_raw = sel.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
    if not next_data_raw:
        return 0

    try:
        data = json.loads(next_data_raw)
    except json.JSONDecodeError:
        return 0

    # La estructura de Walmart anida los productos en varios niveles
    # Intentamos varios paths conocidos
    items = []

    try:
        # Path 1: búsqueda/categoría
        items = (
            data["props"]["pageProps"]["initialData"]["searchResult"]["itemStacks"][0]["items"]
        )
    except (KeyError, IndexError, TypeError):
        pass

    if not items:
        try:
            # Path 2: página de departamento
            items = (
                data["props"]["pageProps"]["initialData"]["contentLayout"]["modules"]
            )
        except (KeyError, TypeError):
            pass

    count = 0
    for item in items:
        try:
            nombre = item.get("name") or item.get("title") or ""
            if not nombre:
                continue

            # Precio — Walmart usa varios campos según el tipo de oferta
            precio_info = item.get("priceInfo") or item.get("price") or {}
            precio = (
                precio_info.get("currentPrice", {}).get("price") or
                precio_info.get("wasPrice", {}).get("price") or
                item.get("price") or
                0
            )
            if isinstance(precio, str):
                precio = float(precio.replace("$", "").replace(",", ""))

            if precio <= 0:
                continue

            marca = item.get("brand") or None
            unidad = item.get("shortDescription") or None

            insertar_producto(
                cadena=cadena,
                item=nombre,
                precio=float(precio),
                fuente=f"{cadena.lower().replace(' ', '')}.com.mx",
                unidad=unidad,
                marca=marca,
                categoria=categoria,
                subcategoria=subcategoria,
            )
            count += 1

        except Exception:
            continue

    return count


def scrape():
    total = 0
    session = requests.Session()

    for cadena, url, categoria, subcategoria in TARGETS:
        try:
            # Delay aleatorio entre 2 y 5 segundos para no parecer bot
            time.sleep(random.uniform(2, 5))

            print(f"  Scrapeando {cadena} — {categoria}...")
            resp = session.get(
                url,
                headers=HEADERS,
                impersonate="chrome124",  # TLS fingerprint de Chrome 124
                timeout=20,
            )

            if resp.status_code == 200:
                count = extraer_productos_next_data(
                    resp.text, cadena, categoria, subcategoria
                )
                print(f"    ✓ {count} productos extraídos")
                total += count
            elif resp.status_code == 403:
                print(f"    ✗ Bloqueado (403) — se omite esta categoría")
            else:
                print(f"    ✗ Status {resp.status_code}")

        except Exception as e:
            print(f"    ✗ Error en {url}: {e}")
            continue

    print(f"  ✓ Total Walmart/Bodega/Sam's: {total} productos")
    return total


if __name__ == "__main__":
    scrape()
