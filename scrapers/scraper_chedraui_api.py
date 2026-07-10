"""
Scraper Chedraui via API interna
Chedraui usa VTEX como plataforma — tiene una API JSON pública
que devuelve productos por categoría sin necesidad de browser.
Método: requests directos a la API de búsqueda de VTEX
"""

import requests
import time
import random
from utils import insertar_producto

FUENTE = "chedraui-api"

# API de búsqueda VTEX de Chedraui
# Devuelve JSON con nombre, precio, categoría sin JavaScript
API_URL = "https://www.chedraui.com.mx/api/catalog_system/pub/products/search"

# Categorías con sus IDs en VTEX de Chedraui
CATEGORIAS = [
    ("Lácteos",          "General",         "/supermercado/lacteos-y-huevo/"),
    ("Frutas y Verduras","General",         "/supermercado/frutas-y-verduras/"),
    ("Carnes",           "General",         "/supermercado/carnes/"),
    ("Abarrotes",        "General",         "/supermercado/abarrotes/"),
    ("Bebidas",          "General",         "/supermercado/bebidas/"),
    ("Limpieza",         "Hogar",           "/supermercado/limpieza-del-hogar/"),
    ("Salud",            "Cuidado personal","/cuidado-personal/"),
    ("Salud",            "Medicamentos",    "/farmacia/"),
    ("Electrónica",      "General",         "/electronica/"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json",
}


def scrape_categoria(categoria: str, subcategoria: str, dept: str) -> int:
    count = 0
    pagina = 0
    por_pagina = 50

    while True:
        params = {
            "fq": f"C:{dept}",
            "_from": pagina * por_pagina,
            "_to": (pagina + 1) * por_pagina - 1,
            "O": "OrderByTopSaleDESC",
        }
        try:
            resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                break

            productos = resp.json()
            if not productos:
                break

            for p in productos:
                nombre = p.get("productName") or p.get("name") or ""
                marca = p.get("brand") or None

                # VTEX anida el precio en items → sellers → commertialOffer
                precio = 0.0
                items = p.get("items", [])
                if items:
                    sellers = items[0].get("sellers", [])
                    if sellers:
                        oferta = sellers[0].get("commertialOffer", {})
                        precio = oferta.get("Price") or oferta.get("ListPrice") or 0.0

                if nombre and precio > 0:
                    insertar_producto(
                        cadena="Chedraui",
                        item=nombre,
                        precio=float(precio),
                        fuente=FUENTE,
                        marca=marca,
                        categoria=categoria,
                        subcategoria=subcategoria,
                    )
                    count += 1

            # Si devolvió menos de por_pagina, ya no hay más
            if len(productos) < por_pagina:
                break

            pagina += 1
            time.sleep(random.uniform(1, 2))

        except Exception as e:
            print(f"    ✗ Error en página {pagina}: {e}")
            break

    return count


def scrape():
    total = 0
    print("  [Chedraui API] iniciando...")
    for categoria, subcategoria, dept in CATEGORIAS:
        time.sleep(random.uniform(2, 4))
        count = scrape_categoria(categoria, subcategoria, dept)
        print(f"    {categoria}: {count} productos")
        total += count
    print(f"  [Chedraui API] ✓ Total: {total}")
    return total


if __name__ == "__main__":
    scrape()
