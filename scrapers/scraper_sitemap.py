"""
Scraper basado en sitemaps XML — URLs reales verificadas
Cubre: Soriana, Chedraui
Método: 
  1. Descarga sitemap XML → obtiene URLs reales de productos
  2. Por cada URL de producto → extrae nombre + precio con Scrapling
"""

import asyncio
import re
import random
import xml.etree.ElementTree as ET
import requests
from scrapling.fetchers import StealthyFetcher
from utils import insertar_producto

# ── Configuración por cadena ──────────────────────────────────────────────────

CADENAS = [
    {
        "cadena": "Soriana",
        "sitemap_index": "https://www.soriana.com/sitemap_index.xml",
        "sitemap_pattern": "product",  # solo sitemaps de productos
        "max_sitemaps": 3,             # limitar para no exceder tiempo de Actions
        "max_productos": 500,
        "precio_selector": "[class*='price-sales'], .price-sales, [itemprop='price']",
        "nombre_selector": "[itemprop='name'], h1.product-name, .product-name",
        "categoria_default": "Supermercado",
        "url_valida": lambda u: u.endswith(".html") and "/p/" not in u,
    },
    {
        "cadena": "Chedraui",
        "sitemap_index": "https://www.chedraui.com.mx/sitemap/sitemap_index.xml",
        "sitemap_pattern": "product",
        "max_sitemaps": 3,
        "max_productos": 500,
        "precio_selector": "[class*='vtex-product-price'], [class*='sellingPrice'], .price",
        "nombre_selector": "[class*='vtex-store-components'] h1, [class*='productName'], h1",
        "categoria_default": "Supermercado",
        "url_valida": lambda u: u.endswith("/p") or "/p?" in u,
    },
]


def obtener_urls_sitemap(sitemap_index_url: str, patron: str, max_sitemaps: int) -> list[str]:
    """
    Descarga el sitemap index y extrae URLs de sitemaps que coincidan con el patrón.
    Luego descarga cada sitemap y extrae las URLs de productos.
    """
    try:
        resp = requests.get(sitemap_index_url, timeout=30,
                           headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            print(f"    ✗ Sitemap index no disponible: {resp.status_code}")
            return []

        # Parsear XML del sitemap index
        root = ET.fromstring(resp.content)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        # Encontrar sitemaps que contengan el patrón
        sitemap_urls = []
        for sitemap in root.findall("sm:sitemap", ns):
            loc = sitemap.find("sm:loc", ns)
            if loc is not None and patron in loc.text:
                sitemap_urls.append(loc.text)

        print(f"    Encontrados {len(sitemap_urls)} sitemaps de {patron}")
        sitemap_urls = sitemap_urls[:max_sitemaps]

        # Descargar cada sitemap y extraer URLs de productos
        product_urls = []
        for sitemap_url in sitemap_urls:
            try:
                resp2 = requests.get(sitemap_url, timeout=30,
                                    headers={"User-Agent": "Mozilla/5.0"})
                if resp2.status_code != 200:
                    continue
                root2 = ET.fromstring(resp2.content)
                for url_el in root2.findall("sm:url", ns):
                    loc = url_el.find("sm:loc", ns)
                    if loc is not None:
                        product_urls.append(loc.text)
            except Exception as e:
                print(f"    ✗ Error descargando {sitemap_url}: {e}")
                continue

        return product_urls

    except Exception as e:
        print(f"    ✗ Error en sitemap index: {e}")
        return []


def limpiar_precio(texto: str) -> float:
    if not texto:
        return 0.0
    limpio = re.sub(r"[^\d.,]", "", texto.strip())
    if "," in limpio and "." in limpio:
        limpio = limpio.replace(",", "")
    elif "," in limpio:
        limpio = limpio.replace(",", ".")
    try:
        return float(limpio)
    except ValueError:
        return 0.0


def inferir_categoria(url: str, nombre: str) -> tuple[str, str]:
    """Infiere categoría desde la URL o nombre del producto."""
    texto = (url + " " + nombre).lower()
    if any(w in texto for w in ["leche", "lacteo", "yogurt", "queso", "crema"]):
        return "Lácteos", "General"
    if any(w in texto for w in ["fruta", "verdura", "jitomate", "cebolla", "manzana"]):
        return "Frutas y Verduras", "General"
    if any(w in texto for w in ["carne", "pollo", "res", "cerdo", "salmon", "atun"]):
        return "Carnes", "General"
    if any(w in texto for w in ["limpieza", "detergente", "jabon", "desinfectante"]):
        return "Limpieza", "Hogar"
    if any(w in texto for w in ["shampoo", "acondicionador", "crema", "desodorante"]):
        return "Salud", "Cuidado personal"
    if any(w in texto for w in ["medicamento", "pastilla", "vitamina", "farmacia"]):
        return "Salud", "Medicamentos"
    if any(w in texto for w in ["refresco", "agua", "jugo", "cerveza", "bebida"]):
        return "Bebidas", "General"
    if any(w in texto for w in ["arroz", "frijol", "pasta", "cereal", "galleta"]):
        return "Abarrotes", "General"
    return "Supermercado", "General"


async def scrape_producto(fetcher, url: str, config: dict) -> bool:
    """Scrapea un producto individual y lo inserta en la base de datos."""
    try:
        page = await fetcher.async_fetch(
            url,
            headless=True,
            network_idle=True,
            timeout=30000,
        )
        if page is None:
            return False

        # Extraer nombre
        nombre = ""
        for sel in config["nombre_selector"].split(", "):
            el = page.css_first(sel.strip())
            if el and el.text.strip():
                nombre = el.text.strip()
                break

        # Si no encontró con CSS, buscar en JSON-LD (más confiable)
        if not nombre:
            ld = page.css_first('script[type="application/ld+json"]')
            if ld:
                import json
                try:
                    data = json.loads(ld.text)
                    if isinstance(data, dict):
                        nombre = data.get("name", "")
                        precio_ld = data.get("offers", {}).get("price")
                        if nombre and precio_ld:
                            cat, subcat = inferir_categoria(url, nombre)
                            insertar_producto(
                                cadena=config["cadena"],
                                item=nombre,
                                precio=float(precio_ld),
                                fuente=f"sitemap:{config['cadena'].lower()}",
                                categoria=cat,
                                subcategoria=subcat,
                            )
                            return True
                except Exception:
                    pass

        # Extraer precio con CSS
        precio = 0.0
        for sel in config["precio_selector"].split(", "):
            el = page.css_first(sel.strip())
            if el:
                p = limpiar_precio(el.text)
                if p > 0:
                    precio = p
                    break

        if nombre and precio > 0:
            cat, subcat = inferir_categoria(url, nombre)
            insertar_producto(
                cadena=config["cadena"],
                item=nombre,
                precio=precio,
                fuente=f"sitemap:{config['cadena'].lower()}",
                categoria=cat,
                subcategoria=subcat,
            )
            return True

        return False

    except Exception:
        return False


async def scrape_async():
    total = 0
    fetcher = StealthyFetcher()

    for config in CADENAS:
        cadena = config["cadena"]
        print(f"\n  [{cadena}] Descargando sitemap...")

        # Obtener URLs reales del sitemap
        urls = obtener_urls_sitemap(
            config["sitemap_index"],
            config["sitemap_pattern"],
            config["max_sitemaps"],
        )

        # Filtrar solo URLs de productos válidas
        urls = [u for u in urls if config["url_valida"](u)]
        # Limitar cantidad para no exceder tiempo de Actions
        urls = urls[:config["max_productos"]]
        # Mezclar aleatoriamente para diversificar categorías
        random.shuffle(urls)

        print(f"  [{cadena}] {len(urls)} URLs de productos a procesar")

        count = 0
        for i, url in enumerate(urls):
            await asyncio.sleep(random.uniform(1.5, 3.0))
            ok = await scrape_producto(fetcher, url, config)
            if ok:
                count += 1
            # Log cada 50 productos
            if (i + 1) % 50 == 0:
                print(f"    Progreso: {i+1}/{len(urls)} — {count} precios obtenidos")

        print(f"  [{cadena}] ✓ {count} precios obtenidos")
        total += count

    return total


def scrape():
    return asyncio.run(scrape_async())


if __name__ == "__main__":
    scrape()
