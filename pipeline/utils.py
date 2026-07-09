"""
Utilidades compartidas para todos los scrapers del pipeline.
- Normalización de texto para búsqueda
- Inserción en productos.db y servicios.db
- Mapeo de cadenas a clase_denue
"""

import sqlite3
import unicodedata
import os
from datetime import date

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "db")
PRODUCTOS_DB = os.path.join(DB_DIR, "productos.db")
SERVICIOS_DB  = os.path.join(DB_DIR, "servicios.db")

# Mapeo de nombre de cadena → clase_denue oficial
# Para que la app pueda hacer match con el DENUE local
CLASE_DENUE = {
    "Walmart":          "Comercio al por menor en supermercados y tiendas de autoservicio",
    "Bodega Aurrerá":   "Comercio al por menor en supermercados y tiendas de autoservicio",
    "Sam's Club":       "Comercio al por menor en clubes de membresía",
    "Soriana":          "Comercio al por menor en supermercados y tiendas de autoservicio",
    "Chedraui":         "Comercio al por menor en supermercados y tiendas de autoservicio",
    "La Comer":         "Comercio al por menor en supermercados y tiendas de autoservicio",
    "H-E-B":            "Comercio al por menor en supermercados y tiendas de autoservicio",
    "Coppel":           "Comercio al por menor de ropa, bisutería y accesorios de vestir",
    "Liverpool":        "Comercio al por menor en tiendas departamentales",
    "Steren":           "Comercio al por menor de equipos y aparatos electrónicos",
    "Farmacias Guadalajara": "Comercio al por menor de medicamentos",
    "Farmacias del Ahorro":  "Comercio al por menor de medicamentos",
    "Benavides":        "Comercio al por menor de medicamentos",
    "Domino's":         "Restaurantes de comida rápida",
    "Profeco":          None,  # fuente oficial, sin cadena específica
}


def normalizar(texto: str) -> str:
    """
    Convierte texto a minúsculas sin acentos ni caracteres especiales.
    Ejemplo: "Jitomate Güero 1kg" → "jitomate guero 1kg"
    """
    if not texto:
        return ""
    texto = texto.lower().strip()
    # Quitar acentos
    nfkd = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Quitar caracteres que no sean letras, números o espacios
    texto = "".join(c if c.isalnum() or c.isspace() else " " for c in texto)
    # Colapsar espacios múltiples
    return " ".join(texto.split())


def hoy() -> str:
    return date.today().isoformat()


def insertar_producto(
    cadena: str,
    item: str,
    precio: float,
    fuente: str,
    unidad: str = None,
    marca: str = None,
    categoria: str = None,
    subcategoria: str = None,
):
    """Inserta un precio de producto en productos.db."""
    if not item or precio <= 0:
        return
    clase = CLASE_DENUE.get(cadena)
    con = sqlite3.connect(PRODUCTOS_DB)
    con.execute("""
        INSERT INTO productos
            (cadena, clase_denue, item, item_norm, precio,
             unidad, marca, categoria, subcategoria, fecha, fuente)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        cadena,
        clase,
        item.strip(),
        normalizar(item),
        round(precio, 2),
        unidad,
        marca,
        categoria,
        subcategoria,
        hoy(),
        fuente,
    ))
    con.commit()
    con.close()


def insertar_servicio(
    cadena: str,
    servicio: str,
    precio: float,
    fuente: str,
    categoria: str = None,
    subcategoria: str = None,
):
    """Inserta un precio de servicio en servicios.db."""
    if not servicio or precio <= 0:
        return
    clase = CLASE_DENUE.get(cadena)
    con = sqlite3.connect(SERVICIOS_DB)
    con.execute("""
        INSERT INTO servicios
            (cadena, clase_denue, servicio, servicio_norm,
             precio, categoria, subcategoria, fecha, fuente)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        cadena,
        clase,
        servicio.strip(),
        normalizar(servicio),
        round(precio, 2),
        categoria,
        subcategoria,
        hoy(),
        fuente,
    ))
    con.commit()
    con.close()


def limpiar_tablas():
    """
    Borra todos los registros antes de cada ejecución del pipeline.
    La base siempre tiene solo los precios más recientes.
    """
    for db_path, tabla in [(PRODUCTOS_DB, "productos"), (SERVICIOS_DB, "servicios")]:
        con = sqlite3.connect(db_path)
        con.execute(f"DELETE FROM {tabla}")
        con.commit()
        con.close()
    print("✓ Tablas limpiadas — listas para datos frescos")
