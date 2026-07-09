"""
Inicializa productos.db y servicios.db con el esquema acordado.
Se ejecuta una vez al inicio del pipeline antes de insertar datos.
"""

import sqlite3
import os

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "db")
os.makedirs(DB_DIR, exist_ok=True)

PRODUCTOS_DB = os.path.join(DB_DIR, "productos.db")
SERVICIOS_DB  = os.path.join(DB_DIR, "servicios.db")


def init_productos():
    con = sqlite3.connect(PRODUCTOS_DB)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id_precio    INTEGER PRIMARY KEY AUTOINCREMENT,
            cadena       TEXT NOT NULL,
            clase_denue  TEXT,
            item         TEXT NOT NULL,
            item_norm    TEXT NOT NULL,
            precio       REAL NOT NULL,
            unidad       TEXT,
            marca        TEXT,
            categoria    TEXT,
            subcategoria TEXT,
            fecha        TEXT NOT NULL,
            fuente       TEXT NOT NULL
        )
    """)
    # Índice para búsqueda rápida por nombre normalizado
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_item_norm
        ON productos(item_norm)
    """)
    # Índice para agrupar por cadena
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_cadena_productos
        ON productos(cadena)
    """)
    con.commit()
    con.close()
    print(f"✓ productos.db inicializada en {PRODUCTOS_DB}")


def init_servicios():
    con = sqlite3.connect(SERVICIOS_DB)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS servicios (
            id_precio    INTEGER PRIMARY KEY AUTOINCREMENT,
            cadena       TEXT NOT NULL,
            clase_denue  TEXT,
            servicio     TEXT NOT NULL,
            servicio_norm TEXT NOT NULL,
            precio       REAL NOT NULL,
            categoria    TEXT,
            subcategoria TEXT,
            fecha        TEXT NOT NULL,
            fuente       TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_servicio_norm
        ON servicios(servicio_norm)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_cadena_servicios
        ON servicios(cadena)
    """)
    con.commit()
    con.close()
    print(f"✓ servicios.db inicializada en {SERVICIOS_DB}")


if __name__ == "__main__":
    init_productos()
    init_servicios()
