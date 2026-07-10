"""
Scraper con Scrapling StealthyFetcher — reemplaza scraper_crawl4ai.py
Cubre: Soriana, Chedraui, La Comer, H-E-B, Steren, Liverpool,
       Farmacias Guadalajara, Farmacias del Ahorro, Benavides
Método: StealthyFetcher (bypass nativo Cloudflare/anti-bot sin proxies)
"""

import asyncio
import re
import time
import random
import json
from scrapling.fetchers import StealthyFetcher
from utils import insertar_producto

# ── Targets ───────────────────────────────────────────────────────────────────

TARGETS = [
    # (cadena, url, categoria, subcategoria)
    ("Soriana", "https://www.soriana.com/comida/lacteos-y-huevo.html",        "Lácteos",         "General"),
    ("Soriana", "https://www.soriana.com/comida/frutas-y-verduras.html",      "Frutas y Verduras","General"),
    ("Soriana", "https://www.soriana.com/comida/carniceria.html",             "Carnes",          "General"),
    ("Soriana", "https://www.soriana.com/comida/abarrotes.html",              "Abarrotes",       "General"),
    ("Soriana", "https://www.soriana.com/comida/bebidas.html",                "Bebidas",         "General"),
    ("Soriana", "https://www.soriana.com/comida/limpieza-del-hogar.html",     "Limpieza",        "Hogar"),

    ("Chedraui", "https://www.chedraui.com.mx/lacteos",                      "Lácteos",         "General"),
    ("Chedraui", "https://www.chedraui.com.mx/frutas-y-verduras",            "Frutas y Verduras","General"),
    ("Chedraui", "https://www.chedraui.com.mx/carnes",                       "Carnes",          "General"),
    ("Chedraui", "https://www.chedraui.com.mx/abarrotes",                    "Abarrotes",       "General"),
    ("Chedraui", "https://www.chedraui.com.mx/bebidas",                      "Bebidas",         "General"),

    ("La Comer", "https://www.lacomer.com.mx/lacomer/#!/pasillo/lacteos",    "Lácteos",         "General"),
    ("La Comer", "https://www.lacomer.com.mx/lacomer/#!/pasillo/frutas",     "Frutas y Verduras","General"),
    ("La Comer", "https://www.lacomer.com.mx/lacomer/#!/pasillo/abarrotes",  "Abarrotes",       "General"),

    ("H-E-B",    "https://www.heb.com.mx/lacteos",                           "Lácteos",         "General"),
    ("H-E-B",    "https://www.heb.com.mx/frutas-y-verduras",                 "Frutas y Verduras","General"),
    ("H-E-B",    "https://www.heb.com.mx/carnes",                            "Carnes",          "General"),
    ("H-E-B",    "https://www.heb.com.mx/abarrotes",                         "Abarrotes",       "General"),

    ("Steren",   "https://www.steren.com.mx/audio",                          "Electrónica",     "Audio"),
    ("Steren",   "https://www.steren.com.mx/cables-y-conectores",            "Electrónica",     "Cables"),
    ("Steren",   "https://www.steren.com.mx/herramientas",                   "Herramientas",    "General"),
    ("Steren",   "https://www.steren.com.mx/computo",                        "Electrónica",     "Cómputo"),

    ("Liverpool", "https://www.liverpool.com.mx/tienda/cat/electrodomesticos","Electrodomésticos","General"),
    ("Liverpool", "https://www.liverpool.com.mx/tienda/cat/telefonia",        "Electrónica",     "Telefonía"),
    ("Liverpool", "https://www.liverpool.com.mx/tienda/cat/linea-blanca",     "Electrodomésticos","Línea blanca"),

    ("Farmacias Guadalajara", "https://www.farmaciasguadalajara.com/medicamentos",    "Salud", "Medicamentos"),
    ("Farmacias Guadalajara", "https://www.farmaciasguadalajara.com/cuidado-personal","Salud", "Cuidado personal"),
    ("Farmacias Guadalajara", "https://www.farmaciasguadalajara.com/vitaminas",       "Salud", "Vitaminas"),

    ("Farmacias del Ahorro",  "https://www.fahorro.com/medicamentos.html",    "Salud", "Medicamentos"),
    ("Farmacias del Ahorro",  "https://www.fahorro.com/vitaminas.html",       "Salud", "Vitaminas"),

    ("Benavides", "https://www.benavides.com.mx/medicamentos",               "Salud", "Medicamentos"),
]

# Selectores CSS por sitio — fallback a genéricos si no hay específico
SELECTORES = {
    "Soriana": {
        "contenedor": ".product-tile, .plp-product-card",
        "nombre":     ".product-title, .plp-product-name",
        "precio":     ".product-price .value, .plp-price",
        "marca":      ".product-brand",
    },
    "Chedraui": {
        "contenedor": "[class*='ProductCard'], [class*='product-card']",
        "nombre":     "[class*='ProductName'], [class*='product-name']",
        "precio":     "[class*='Price']:not([class*='Old']):not([class*='Strike'])",
        "marca":      "[class*='Brand'], [class*='brand']",
    },
    "Steren": {
        "contenedor": ".product-item, [class*='product-card']",
        "nombre":     ".product-item-link, [class*='product-name']",
        "precio":     ".price, [class*='price']",
        "marca":      None,
    },
    "Liverpool": {
        "contenedor": "[class*='product'], [class*='Product']",
        "nombre":     "[class*='name'], [class*='Name'], h3",
        "precio":     "[class*='price']:not([class*='old']):not([class*='before'])",
        "marca":      "[class*='brand'], [class*='Brand']",
    },
    "Farmacias Guadalajara": {
        "contenedor": ".product-item, [class*='product-card']",
        "nombre":     ".product-item-link, [class*='name']",
        "precio":     ".price, [class*='price']",
        "marca":      "[class*='brand'], [class*='manufacturer']",
    },
    # Genérico para el resto
    "_default": {
        "contenedor": "[class*='product'], [class*='item-card'], [class*='card']",
        "nombre":     "[class*='name'], [class*='title'], h2, h3",
        "precio":     "[class*='price'], [class*='Price'], [class*='costo']",
        "marca":      "[class*='brand'], [class*='marca']",
    },
}


def limpiar_precio(texto: str) -> float:
    if not texto:
        return 0.0
    # Quitar símbolos de moneda, espacios, texto extra
    limpio = re.sub(r"[^\d.,]", "", texto.strip())
    # Normalizar coma decimal
    if "," in limpio and "." in limpio:
        limpio = limpio.replace(",", "")
    elif "," in limpio:
        limpio = limpio.replace(",", ".")
    try:
        return float(limpio)
    except ValueError:
        return 0.0


def extraer_con_selectores(page, cadena: str, categoria: str, subcategoria: str) -> int:
    """Extrae productos usando selectores CSS con Scrapling."""
    sels = SELECTORES.get(cadena, SELECTORES["_default"])
    count = 0

    try:
        contenedores = page.css(sels["contenedor"])
        for item in contenedores:
            try:
                # Nombre
                nombre_el = item.css_first(sels["nombre"])
                nombre = nombre_el.text.strip() if nombre_el else ""

                # Precio — tomar el primero que sea número válido
                precio = 0.0
                for pel in item.css(sels["precio"]):
                    p = limpiar_precio(pel.text)
                    if p > 0:
                        precio = p
                        break

                # Marca (opcional)
                marca = None
                if sels.get("marca"):
                    marca_el = item.css_first(sels["marca"])
                    marca = marca_el.text.strip() if marca_el else None

                if nombre and precio > 0:
                    insertar_producto(
                        cadena=cadena,
                        item=nombre,
                        precio=precio,
                        fuente=f"scrapling:{cadena.lower().replace(' ', '')}",
                        marca=marca,
                        categoria=categoria,
                        subcategoria=subcategoria,
                    )
                    count += 1

            except Exception:
                continue

    except Exception as e:
        pass

    return count


def extraer_json_embebido(html: str, cadena: str, categoria: str, subcategoria: str) -> int:
    """
    Fallback: busca JSON embebido en el HTML con patrones de precio.
    Útil cuando el CSS no encuentra nada pero hay datos en window.__STATE__ etc.
    """
    count = 0
    # Busca bloques JSON que contengan "price" y "name"
    patrones = [
        r'"name"\s*:\s*"([^"]{3,100})"[^}]*"price"\s*:\s*([\d.]+)',
        r'"title"\s*:\s*"([^"]{3,100})"[^}]*"price"\s*:\s*([\d.]+)',
        r'"nombre"\s*:\s*"([^"]{3,100})"[^}]*"precio"\s*:\s*([\d.]+)',
    ]
    encontrados = set()
    for patron in patrones:
        for match in re.finditer(patron, html):
            nombre = match.group(1).strip()
            try:
                precio = float(match.group(2))
            except ValueError:
                continue
            clave = f"{nombre}:{precio}"
            if nombre and precio > 0 and clave not in encontrados:
                encontrados.add(clave)
                insertar_producto(
                    cadena=cadena,
                    item=nombre,
                    precio=precio,
                    fuente=f"scrapling-json:{cadena.lower().replace(' ', '')}",
                    categoria=categoria,
                    subcategoria=subcategoria,
                )
                count += 1
    return count


async def scrape_async():
    total = 0
    fetcher = StealthyFetcher()

    for cadena, url, categoria, subcategoria in TARGETS:
        await asyncio.sleep(random.uniform(3, 7))
        print(f"  Scrapling → {cadena} | {categoria}...")

        try:
            page = await fetcher.async_fetch(
                url,
                headless=True,
                network_idle=True,       # espera a que carguen todos los requests XHR
                timeout=45000,
            )

            if page is None:
                print(f"    ✗ Sin respuesta")
                continue

            # Intento 1: selectores CSS
            count = extraer_con_selectores(page, cadena, categoria, subcategoria)

            # Intento 2: JSON embebido si CSS no encontró nada
            if count == 0:
                count = extraer_json_embebido(page.html, cadena, categoria, subcategoria)

            symbol = "✓" if count > 0 else "✗"
            print(f"    {symbol} {count} productos")
            total += count

        except Exception as e:
            print(f"    ✗ Error: {e}")
            continue

    print(f"  ✓ Total Scrapling: {total} productos")
    return total


def scrape():
    return asyncio.run(scrape_async())


if __name__ == "__main__":
    scrape()
