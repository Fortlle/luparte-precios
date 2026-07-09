"""
Scraper Profeco — Quién es Quién en los Precios
Fuente: datos.gob.mx / profeco.gob.mx
Método: descarga directa de CSV, sin scraping
Cobertura: abarrotes, lácteos, carnes, frutas, medicamentos, electrónicos
"""

import csv
import io
import re
import requests
from utils import insertar_producto, normalizar

FUENTE = "profeco"

# URLs de los datasets públicos de Profeco QQP
# Se actualizan periódicamente — se verifican las dos más recientes
URLS_CSV = [
    "https://datos.profeco.gob.mx/datos_abiertos/qqp/datos_qqp_2026.csv",
    "https://datos.profeco.gob.mx/datos_abiertos/qqp/datos_qqp_2025.csv",
]

# Mapeo de categorías Profeco → subcategorías Luparte
CATEGORIA_MAP = {
    "Aceites y grasas":           ("Abarrotes", "Aceites"),
    "Bebidas":                    ("Bebidas", "General"),
    "Carnes y embutidos":         ("Carnes", "General"),
    "Frutas y verduras":          ("Frutas y Verduras", "General"),
    "Lácteos":                    ("Lácteos", "General"),
    "Limpieza del hogar":         ("Limpieza", "Hogar"),
    "Medicamentos":               ("Salud", "Medicamentos"),
    "Pan y cereales":             ("Abarrotes", "Pan y cereales"),
    "Leguminosas y semillas":     ("Abarrotes", "Leguminosas"),
    "Electrónica":                ("Electrónica", "General"),
    "Artículos escolares":        ("Papelería", "Escolar"),
}


def limpiar_precio(valor: str) -> float:
    """Extrae el número de un string como '$23.50' o '23,50'."""
    if not valor:
        return 0.0
    limpio = re.sub(r"[^\d.]", "", valor.replace(",", "."))
    try:
        return float(limpio)
    except ValueError:
        return 0.0


def detectar_cadena(nombre_comercio: str) -> str:
    """Intenta identificar la cadena a partir del nombre del establecimiento."""
    nombre = nombre_comercio.upper()
    if "WALMART" in nombre:        return "Walmart"
    if "BODEGA" in nombre:         return "Bodega Aurrerá"
    if "SAM'S" in nombre or "SAMS" in nombre: return "Sam's Club"
    if "SORIANA" in nombre:        return "Soriana"
    if "CHEDRAUI" in nombre:       return "Chedraui"
    if "COMER" in nombre:          return "La Comer"
    if "HEB" in nombre or "H-E-B" in nombre: return "H-E-B"
    if "COSTCO" in nombre:         return "Costco"
    if "LIVERPOOL" in nombre:      return "Liverpool"
    if "COPPEL" in nombre:         return "Coppel"
    if "BENAVIDES" in nombre:      return "Benavides"
    if "AHORRO" in nombre:         return "Farmacias del Ahorro"
    if "GUADALAJARA" in nombre:    return "Farmacias Guadalajara"
    # Si no identifica cadena, usa el nombre real
    return nombre_comercio.title()


def scrape():
    total = 0
    for url in URLS_CSV:
        try:
            print(f"  Descargando {url}...")
            resp = requests.get(url, timeout=60)
            if resp.status_code != 200:
                print(f"  ✗ No disponible: {resp.status_code}")
                continue

            # Detectar encoding — Profeco a veces usa latin-1
            try:
                contenido = resp.content.decode("utf-8")
            except UnicodeDecodeError:
                contenido = resp.content.decode("latin-1")

            reader = csv.DictReader(io.StringIO(contenido))

            for fila in reader:
                # Profeco QQP — campos típicos del CSV
                # (los nombres exactos pueden variar por año, se intenta varios)
                nombre_producto = (
                    fila.get("producto") or
                    fila.get("Producto") or
                    fila.get("PRODUCTO") or ""
                ).strip()

                precio_str = (
                    fila.get("precio") or
                    fila.get("Precio") or
                    fila.get("PRECIO") or "0"
                )

                comercio = (
                    fila.get("establecimiento") or
                    fila.get("Establecimiento") or
                    fila.get("ESTABLECIMIENTO") or
                    fila.get("cadena") or ""
                ).strip()

                categoria_raw = (
                    fila.get("categoria") or
                    fila.get("Categoria") or
                    fila.get("CATEGORIA") or ""
                ).strip()

                unidad = (
                    fila.get("presentacion") or
                    fila.get("Presentacion") or
                    fila.get("unidad") or ""
                ).strip()

                marca = (
                    fila.get("marca") or
                    fila.get("Marca") or ""
                ).strip()

                precio = limpiar_precio(precio_str)
                if not nombre_producto or precio <= 0:
                    continue

                cadena = detectar_cadena(comercio) if comercio else "Profeco"
                cat_info = CATEGORIA_MAP.get(categoria_raw, (categoria_raw or "General", "General"))

                insertar_producto(
                    cadena=cadena,
                    item=nombre_producto,
                    precio=precio,
                    fuente=FUENTE,
                    unidad=unidad or None,
                    marca=marca or None,
                    categoria=cat_info[0],
                    subcategoria=cat_info[1],
                )
                total += 1

            print(f"  ✓ {total} precios insertados desde Profeco")
            break  # Si el primer URL funcionó, no necesitamos el segundo

        except Exception as e:
            print(f"  ✗ Error procesando {url}: {e}")
            continue

    return total


if __name__ == "__main__":
    scrape()
