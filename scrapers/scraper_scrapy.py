"""
Scraper Scrapy + Playwright
Cubre: Coppel (precio de contado), Domino's México (menú API interna)
Método: Playwright para JS pesado + intercepción de XHR para Domino's
"""

import scrapy
import json
import re
import subprocess
import sys
import os
from utils import insertar_producto, insertar_servicio

# ── Coppel ────────────────────────────────────────────────────────────────────

class CoppelSpider(scrapy.Spider):
    name = "coppel"
    custom_settings = {
        "DOWNLOAD_HANDLERS": {
            "http":  "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {"headless": True},
        "DOWNLOAD_DELAY": 3,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "LOG_LEVEL": "ERROR",
    }

    start_urls = [
        "https://www.coppel.com/electronica",
        "https://www.coppel.com/linea-blanca",
        "https://www.coppel.com/muebles",
        "https://www.coppel.com/celulares-y-tablets",
        "https://www.coppel.com/ropa-de-hombre",
        "https://www.coppel.com/ropa-de-mujer",
        "https://www.coppel.com/calzado",
        "https://www.coppel.com/herramientas",
    ]

    CATEGORIA_MAP = {
        "electronica":       ("Electrónica", "General"),
        "linea-blanca":      ("Electrodomésticos", "Línea blanca"),
        "muebles":           ("Hogar", "Muebles"),
        "celulares-tablets": ("Electrónica", "Telefonía"),
        "ropa-de-hombre":    ("Ropa", "Hombre"),
        "ropa-de-mujer":     ("Ropa", "Mujer"),
        "calzado":           ("Ropa", "Calzado"),
        "herramientas":      ("Herramientas", "General"),
    }

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta={"playwright": True, "playwright_include_page": True},
                callback=self.parse,
            )

    async def parse(self, response):
        # Detectar categoría desde la URL
        slug = response.url.split("/")[-1]
        cat_info = self.CATEGORIA_MAP.get(slug, ("General", "General"))

        # Coppel carga productos en JSON dentro de window.__INITIAL_STATE__
        # o en llamadas XHR — intentamos ambos
        initial_state = response.xpath(
            '//script[contains(text(),"__INITIAL_STATE__")]/text()'
        ).re_first(r"__INITIAL_STATE__\s*=\s*({.+?});")

        count = 0
        if initial_state:
            try:
                data = json.loads(initial_state)
                productos = (
                    data.get("plp", {})
                        .get("products", [])
                )
                for p in productos:
                    nombre = p.get("name") or p.get("title") or ""
                    # Coppel distingue precio contado vs crédito
                    precio = (
                        p.get("priceContado") or
                        p.get("price", {}).get("contado") or
                        p.get("offerPrice") or
                        p.get("regularPrice") or
                        0
                    )
                    if isinstance(precio, str):
                        precio = float(re.sub(r"[^\d.]", "", precio) or 0)

                    marca = p.get("brand") or None
                    if nombre and float(precio) > 0:
                        insertar_producto(
                            cadena="Coppel",
                            item=nombre,
                            precio=float(precio),
                            fuente="coppel.com",
                            marca=marca,
                            categoria=cat_info[0],
                            subcategoria=cat_info[1],
                        )
                        count += 1
            except Exception as e:
                self.logger.error(f"Error parseando Coppel JSON: {e}")
        else:
            # Fallback: selectores CSS
            for card in response.css("[class*='product-card'], [class*='ProductCard']"):
                nombre = card.css("[class*='name'], [class*='title']::text").get("").strip()
                precio_txt = card.css("[class*='price-contado'], [class*='priceContado']::text").get("") or \
                             card.css("[class*='price']::text").get("") or ""
                precio = float(re.sub(r"[^\d.]", "", precio_txt.replace(",", "")) or 0)
                marca = card.css("[class*='brand']::text").get("") or None

                if nombre and precio > 0:
                    insertar_producto(
                        cadena="Coppel",
                        item=nombre,
                        precio=precio,
                        fuente="coppel.com",
                        marca=marca or None,
                        categoria=cat_info[0],
                        subcategoria=cat_info[1],
                    )
                    count += 1

        print(f"    Coppel {slug}: {count} productos")


# ── Domino's México ───────────────────────────────────────────────────────────

class DominosSpider(scrapy.Spider):
    """
    Domino's expone su menú via API interna JSON.
    Interceptamos la llamada que hace el sitio web al cargar el menú.
    El store_id 1 es representativo para precio nacional.
    """
    name = "dominos"
    custom_settings = {
        "DOWNLOAD_HANDLERS": {
            "http":  "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {"headless": True},
        "LOG_LEVEL": "ERROR",
    }

    # Endpoint interno de Domino's México
    API_MENU = "https://www.dominos.com.mx/power/store/1/menu?lang=es&requestedProductCodes=All"

    start_urls = [API_MENU]

    def parse(self, response):
        try:
            data = response.json()
        except Exception:
            print("    ✗ Domino's: no se pudo parsear JSON del menú")
            return

        count = 0
        # El menú de Domino's tiene categorías con productos anidados
        categories = data.get("categories", {})
        for cat_key, cat_data in categories.items():
            categoria_nombre = cat_data.get("name", cat_key)
            productos = cat_data.get("products", [])

            for prod_key in productos:
                # Los productos vienen referenciados por clave
                prod = data.get("products", {}).get(prod_key, {})
                if not prod:
                    continue

                nombre = prod.get("name") or prod.get("description") or ""
                # Domino's tiene variantes de tamaño con precios distintos
                variants = prod.get("variants", [])
                for variant in variants:
                    precio = variant.get("price") or 0
                    tamano = variant.get("name") or variant.get("size") or ""
                    nombre_completo = f"{nombre} {tamano}".strip() if tamano else nombre

                    if nombre_completo and float(precio) > 0:
                        insertar_servicio(
                            cadena="Domino's",
                            servicio=nombre_completo,
                            precio=float(precio),
                            fuente="dominos.com.mx",
                            categoria="Restaurantes",
                            subcategoria="Pizza",
                        )
                        count += 1

        print(f"    ✓ Domino's: {count} items del menú")


# ── Runner ─────────────────────────────────────────────────────────────────────

def scrape():
    """Ejecuta ambos spiders de Scrapy en secuencia."""
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings

    process = CrawlerProcess(settings={
        "LOG_LEVEL": "ERROR",
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
    })

    process.crawl(CoppelSpider)
    process.crawl(DominosSpider)
    process.start()


if __name__ == "__main__":
    scrape()
