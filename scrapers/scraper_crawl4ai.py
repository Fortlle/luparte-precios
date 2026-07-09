"""
Scraper con Crawl4AI — sitios de dificultad media
Cubre: Soriana, Chedraui, La Comer, H-E-B, Steren, Liverpool,
       Farmacias Guadalajara, Farmacias del Ahorro, Benavides
Método: Playwright headless + extracción CSS/JSON
"""

import asyncio
import json
import re
import time
import random
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from utils import insertar_producto

# ── Esquemas de extracción por sitio ─────────────────────────────────────────
# Cada esquema define los selectores CSS para extraer nombre y precio

ESQUEMA_SORIANA = {
    "name": "productos_soriana",
    "baseSelector": ".product-tile, .plp-product-card, [class*='product-item']",
    "fields": [
        {"name": "nombre", "selector": ".product-title, .plp-product-name, [class*='product-name']", "type": "text"},
        {"name": "precio", "selector": ".product-price, .plp-price, [class*='price']", "type": "text"},
        {"name": "marca",  "selector": ".product-brand, [class*='brand']", "type": "text"},
    ]
}

ESQUEMA_CHEDRAUI = {
    "name": "productos_chedraui",
    "baseSelector": ".product-card, [class*='ProductCard'], [class*='product-tile']",
    "fields": [
        {"name": "nombre", "selector": "[class*='product-name'], [class*='ProductName'], h3", "type": "text"},
        {"name": "precio", "selector": "[class*='price'], [class*='Price']", "type": "text"},
        {"name": "marca",  "selector": "[class*='brand'], [class*='Brand']", "type": "text"},
    ]
}

ESQUEMA_GENERICO = {
    "name": "productos_generico",
    "baseSelector": "[class*='product'], [class*='item-card'], [class*='card-product']",
    "fields": [
        {"name": "nombre", "selector": "[class*='name'], [class*='title'], h2, h3", "type": "text"},
        {"name": "precio", "selector": "[class*='price'], [class*='Price'], [class*='costo']", "type": "text"},
        {"name": "marca",  "selector": "[class*='brand'], [class*='marca']", "type": "text"},
    ]
}

# ── Targets por sitio ─────────────────────────────────────────────────────────

TARGETS = [
    # (cadena, url, esquema, categoria, subcategoria)
    ("Soriana", "https://www.soriana.com/comida/lacteos-y-huevo.html",
     ESQUEMA_SORIANA, "Lácteos", "General"),
    ("Soriana", "https://www.soriana.com/comida/frutas-y-verduras.html",
     ESQUEMA_SORIANA, "Frutas y Verduras", "General"),
    ("Soriana", "https://www.soriana.com/comida/carniceria.html",
     ESQUEMA_SORIANA, "Carnes", "General"),
    ("Soriana", "https://www.soriana.com/comida/abarrotes.html",
     ESQUEMA_SORIANA, "Abarrotes", "General"),
    ("Soriana", "https://www.soriana.com/comida/bebidas.html",
     ESQUEMA_SORIANA, "Bebidas", "General"),

    ("Chedraui", "https://www.chedraui.com.mx/lacteos",
     ESQUEMA_CHEDRAUI, "Lácteos", "General"),
    ("Chedraui", "https://www.chedraui.com.mx/frutas-y-verduras",
     ESQUEMA_CHEDRAUI, "Frutas y Verduras", "General"),
    ("Chedraui", "https://www.chedraui.com.mx/carnes",
     ESQUEMA_CHEDRAUI, "Carnes", "General"),
    ("Chedraui", "https://www.chedraui.com.mx/abarrotes",
     ESQUEMA_CHEDRAUI, "Abarrotes", "General"),

    ("La Comer", "https://www.lacomer.com.mx/lacomer/#!/pasillo/lacteos",
     ESQUEMA_GENERICO, "Lácteos", "General"),
    ("La Comer", "https://www.lacomer.com.mx/lacomer/#!/pasillo/frutas-y-verduras",
     ESQUEMA_GENERICO, "Frutas y Verduras", "General"),

    ("H-E-B", "https://www.heb.com.mx/lacteos",
     ESQUEMA_GENERICO, "Lácteos", "General"),
    ("H-E-B", "https://www.heb.com.mx/frutas-y-verduras",
     ESQUEMA_GENERICO, "Frutas y Verduras", "General"),
    ("H-E-B", "https://www.heb.com.mx/carnes",
     ESQUEMA_GENERICO, "Carnes", "General"),

    ("Steren", "https://www.steren.com.mx/audio",
     ESQUEMA_GENERICO, "Electrónica", "Audio"),
    ("Steren", "https://www.steren.com.mx/cables-y-conectores",
     ESQUEMA_GENERICO, "Electrónica", "Cables"),
    ("Steren", "https://www.steren.com.mx/herramientas",
     ESQUEMA_GENERICO, "Herramientas", "General"),

    ("Liverpool", "https://www.liverpool.com.mx/tienda/cat/electrodomesticos",
     ESQUEMA_GENERICO, "Electrodomésticos", "General"),
    ("Liverpool", "https://www.liverpool.com.mx/tienda/cat/telefonia",
     ESQUEMA_GENERICO, "Electrónica", "Telefonía"),

    ("Farmacias Guadalajara", "https://www.farmaciasguadalajara.com/medicamentos",
     ESQUEMA_GENERICO, "Salud", "Medicamentos"),
    ("Farmacias Guadalajara", "https://www.farmaciasguadalajara.com/cuidado-personal",
     ESQUEMA_GENERICO, "Salud", "Cuidado personal"),

    ("Farmacias del Ahorro", "https://www.fahorro.com/medicamentos.html",
     ESQUEMA_GENERICO, "Salud", "Medicamentos"),

    ("Benavides", "https://www.benavides.com.mx/medicamentos",
     ESQUEMA_GENERICO, "Salud", "Medicamentos"),
]


def limpiar_precio(texto: str) -> float:
    """Extrae float de strings como '$23.50', '23,50', '$ 1,299.00'"""
    if not texto:
        return 0.0
    limpio = re.sub(r"[^\d.]", "", texto.replace(",", ""))
    try:
        return float(limpio)
    except ValueError:
        return 0.0


async def scrape_url(crawler, cadena, url, esquema, categoria, subcategoria) -> int:
    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        extraction_strategy=JsonCssExtractionStrategy(esquema),
        wait_for="css:[class*='product']",   # espera a que carguen productos
        page_timeout=30000,
        delay_before_return_html=2.0,         # 2 seg extra para JS pesado
    )

    try:
        result = await crawler.arun(url=url, config=config)
        if not result.success or not result.extracted_content:
            return 0

        items = json.loads(result.extracted_content)
        if not isinstance(items, list):
            return 0

        count = 0
        for item in items:
            nombre = (item.get("nombre") or "").strip()
            precio = limpiar_precio(item.get("precio") or "")
            marca  = (item.get("marca") or "").strip() or None

            if not nombre or precio <= 0:
                continue

            insertar_producto(
                cadena=cadena,
                item=nombre,
                precio=precio,
                fuente=f"crawl4ai:{url.split('/')[2]}",
                marca=marca,
                categoria=categoria,
                subcategoria=subcategoria,
            )
            count += 1

        return count

    except Exception as e:
        print(f"    ✗ Error en {url}: {e}")
        return 0


async def scrape_async():
    total = 0
    async with AsyncWebCrawler() as crawler:
        for cadena, url, esquema, categoria, subcategoria in TARGETS:
            print(f"  Crawl4AI → {cadena} — {categoria}...")
            # Delay entre requests para no saturar
            await asyncio.sleep(random.uniform(3, 6))
            count = await scrape_url(crawler, cadena, url, esquema, categoria, subcategoria)
            print(f"    {'✓' if count > 0 else '✗'} {count} productos")
            total += count

    print(f"  ✓ Total Crawl4AI: {total} productos")
    return total


def scrape():
    return asyncio.run(scrape_async())


if __name__ == "__main__":
    scrape()
