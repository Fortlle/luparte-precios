"""
Pipeline principal — luparte-precios v2
Orden:
1. Profeco QQP (CSV oficial — más confiable)
2. Walmart curl_cffi + __NEXT_DATA__
3. Chedraui API interna VTEX (sin browser, JSON directo)
4. Soriana via sitemap XML + Scrapling
5. Scrapy + Playwright (Coppel, Domino's)
"""

import sys
import os
import sqlite3
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scrapers"))

from init_db import init_productos, init_servicios
from utils import limpiar_tablas, PRODUCTOS_DB, SERVICIOS_DB


def contar(db_path, tabla):
    try:
        con = sqlite3.connect(db_path)
        n = con.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
        con.close()
        return n
    except Exception:
        return 0


def ejecutar(nombre, fn):
    print(f"\n{'='*50}\n  [{nombre}] iniciando...")
    t = time.time()
    try:
        r = fn()
        dur = round(time.time() - t, 1)
        print(f"  [{nombre}] ✓ completado en {dur}s")
        return r or 0
    except Exception as e:
        dur = round(time.time() - t, 1)
        print(f"  [{nombre}] ✗ error en {dur}s: {e}")
        return 0


def main():
    inicio = time.time()
    print(f"\n{'='*50}")
    print(f"  LUPARTE PRECIOS — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    print("\n[1/7] Inicializando bases...")
    init_productos()
    init_servicios()

    print("\n[2/7] Limpiando datos anteriores...")
    limpiar_tablas()

    print("\n[3/7] Profeco QQP (fuente oficial)...")
    from scraper_profeco import scrape as sp
    ejecutar("Profeco", sp)

    print("\n[4/7] Walmart + Bodega + Sam's (curl_cffi + __NEXT_DATA__)...")
    from scraper_walmart import scrape as sw
    ejecutar("Walmart", sw)

    print("\n[5/7] Chedraui (API interna VTEX)...")
    from scraper_chedraui_api import scrape as sc
    ejecutar("Chedraui API", sc)

    print("\n[6/7] Soriana (sitemap XML + Scrapling)...")
    from scraper_sitemap import scrape as ss
    ejecutar("Soriana Sitemap", ss)

    print("\n[7/7] Scrapy + Playwright (Coppel, Domino's)...")
    from scraper_scrapy import scrape as scrapy_scrape
    ejecutar("Scrapy", scrapy_scrape)

    # Reporte final
    tp = contar(PRODUCTOS_DB, "productos")
    ts = contar(SERVICIOS_DB, "servicios")

    print(f"\n{'='*50}")
    print(f"  REPORTE FINAL")
    print(f"{'='*50}")
    print(f"  productos.db → {tp:,}")
    print(f"  servicios.db  → {ts:,}")
    print(f"  Total         → {tp+ts:,}")
    print(f"  Duración      → {round(time.time()-inicio, 1)}s")

    # Desglose por fuente
    try:
        con = sqlite3.connect(PRODUCTOS_DB)
        print(f"\n  Por fuente:")
        for r in con.execute("SELECT fuente, COUNT(*) FROM productos GROUP BY fuente ORDER BY COUNT(*) DESC"):
            print(f"    {r[0]}: {r[1]:,}")
        con.close()
    except Exception:
        pass

    print(f"{'='*50}\n")

    version = datetime.now().strftime("%Y-%m-%d")
    vf = os.path.join(os.path.dirname(__file__), "..", "db", "version.txt")
    with open(vf, "w") as f:
        f.write(version)
    print(f"  version.txt → {version}")

    if tp + ts == 0:
        print("  ✗ Sin precios — revisar scrapers")
        sys.exit(1)

    print("  ✓ Pipeline completado")


if __name__ == "__main__":
    main()
