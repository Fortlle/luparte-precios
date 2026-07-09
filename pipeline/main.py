"""
Pipeline principal — luparte-precios
Orquesta todos los scrapers en orden, limpia las bases antes de cada ejecución,
y genera un reporte final con el conteo de precios obtenidos por fuente.

Orden de ejecución:
1. Profeco QQP (CSV oficial, más confiable)
2. Walmart/Bodega/Sam's (curl_cffi + __NEXT_DATA__)
3. Crawl4AI (Soriana, Chedraui, La Comer, H-E-B, Steren, Liverpool, Farmacias)
4. Scrapy + Playwright (Coppel, Domino's)
"""

import sys
import os
import sqlite3
import time
from datetime import datetime

# Asegurar que los módulos del pipeline y scrapers estén en el path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scrapers"))

from init_db import init_productos, init_servicios
from utils import limpiar_tablas, PRODUCTOS_DB, SERVICIOS_DB


def contar_registros(db_path: str, tabla: str) -> int:
    try:
        con = sqlite3.connect(db_path)
        count = con.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
        con.close()
        return count
    except Exception:
        return 0


def ejecutar_scraper(nombre: str, fn):
    print(f"\n{'='*50}")
    print(f"  [{nombre}] iniciando...")
    inicio = time.time()
    try:
        resultado = fn()
        duracion = round(time.time() - inicio, 1)
        print(f"  [{nombre}] ✓ completado en {duracion}s")
        return resultado or 0
    except Exception as e:
        duracion = round(time.time() - inicio, 1)
        print(f"  [{nombre}] ✗ error después de {duracion}s: {e}")
        return 0


def main():
    inicio_total = time.time()
    print(f"\n{'='*50}")
    print(f"  LUPARTE PRECIOS — Pipeline")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    # 1. Inicializar bases de datos
    print("\n[1/6] Inicializando bases de datos...")
    init_productos()
    init_servicios()

    # 2. Limpiar datos anteriores
    print("\n[2/6] Limpiando datos anteriores...")
    limpiar_tablas()

    # 3. Profeco QQP
    print("\n[3/6] Profeco QQP (fuente oficial)...")
    from scraper_profeco import scrape as scrape_profeco
    ejecutar_scraper("Profeco", scrape_profeco)

    # 4. Walmart / Bodega Aurrerá / Sam's Club
    print("\n[4/6] Walmart + Bodega Aurrerá + Sam's Club (curl_cffi)...")
    from scraper_walmart import scrape as scrape_walmart
    ejecutar_scraper("Walmart", scrape_walmart)

    # 5. Crawl4AI — sitios de dificultad media
    print("\n[5/6] Crawl4AI (Soriana, Chedraui, La Comer, H-E-B, Steren, Liverpool, Farmacias)...")
    from scraper_crawl4ai import scrape as scrape_crawl4ai
    ejecutar_scraper("Crawl4AI", scrape_crawl4ai)

    # 6. Scrapy + Playwright — Coppel y Domino's
    print("\n[6/6] Scrapy + Playwright (Coppel, Domino's)...")
    from scraper_scrapy import scrape as scrape_scrapy
    ejecutar_scraper("Scrapy", scrape_scrapy)

    # Reporte final
    duracion_total = round(time.time() - inicio_total, 1)
    total_productos = contar_registros(PRODUCTOS_DB, "productos")
    total_servicios = contar_registros(SERVICIOS_DB, "servicios")

    print(f"\n{'='*50}")
    print(f"  REPORTE FINAL")
    print(f"{'='*50}")
    print(f"  productos.db → {total_productos:,} precios")
    print(f"  servicios.db  → {total_servicios:,} precios")
    print(f"  Total         → {total_productos + total_servicios:,} precios")
    print(f"  Duración      → {duracion_total}s")
    print(f"  Fecha         → {datetime.now().strftime('%Y-%m-%d')}")
    print(f"{'='*50}\n")

    # Escribir versión para que la app sepa si hay actualización
    version_file = os.path.join(os.path.dirname(__file__), "..", "db", "version.txt")
    with open(version_file, "w") as f:
        f.write(datetime.now().strftime("%Y-%m-%d"))
    print(f"  version.txt → {datetime.now().strftime('%Y-%m-%d')}")

    # Exit code 1 si no se obtuvo nada (para que GitHub Actions marque el job como fallido)
    if total_productos + total_servicios == 0:
        print("  ✗ No se obtuvieron precios — revisar scrapers")
        sys.exit(1)

    print("  ✓ Pipeline completado exitosamente")


if __name__ == "__main__":
    main()
