# luparte-precios

Pipeline automatizado de precios para la app Luparte.
Se ejecuta en GitHub Actions cada 20 días y publica las bases de datos
como release para que la app las descargue.

## Estructura

```
luparte-precios/
├── .github/
│   └── workflows/
│       └── pipeline.yml      # workflow de GitHub Actions
├── pipeline/
│   ├── init_db.py            # inicializa los esquemas SQLite
│   ├── utils.py              # utilidades compartidas (normalización, inserción)
│   └── main.py               # orquestador principal
├── scrapers/
│   ├── scraper_profeco.py    # Profeco QQP (CSV oficial)
│   ├── scraper_walmart.py    # Walmart / Bodega Aurrerá / Sam's (curl_cffi)
│   ├── scraper_crawl4ai.py   # Soriana / Chedraui / La Comer / HEB / Steren / Liverpool / Farmacias
│   └── scraper_scrapy.py     # Coppel / Domino's (Scrapy + Playwright)
├── db/                       # generado en el pipeline, no se sube al repo
│   ├── productos.db
│   ├── servicios.db
│   └── version.txt
├── requirements.txt
└── README.md
```

## Bases de datos generadas

### productos.db
| Campo        | Tipo    | Descripción                              |
|-------------|---------|------------------------------------------|
| id_precio   | INTEGER | Clave primaria                           |
| cadena      | TEXT    | Walmart, Soriana, Chedraui...            |
| clase_denue | TEXT    | Clasificación oficial DENUE              |
| item        | TEXT    | Nombre del producto                      |
| item_norm   | TEXT    | Nombre normalizado para búsqueda         |
| precio      | REAL    | Precio en pesos MXN                      |
| unidad      | TEXT    | kg, pieza, 1L, etc.                      |
| marca       | TEXT    | Marca del producto (si está disponible)  |
| categoria   | TEXT    | Lácteos, Frutas, Electrónica...          |
| subcategoria| TEXT    | Subdivisión de categoría                 |
| fecha       | TEXT    | YYYY-MM-DD                               |
| fuente      | TEXT    | profeco, walmart.com.mx, crawl4ai:...    |

### servicios.db
| Campo         | Tipo    | Descripción                              |
|--------------|---------|------------------------------------------|
| id_precio    | INTEGER | Clave primaria                           |
| cadena       | TEXT    | Domino's, etc.                           |
| clase_denue  | TEXT    | Clasificación oficial DENUE              |
| servicio     | TEXT    | Nombre del servicio                      |
| servicio_norm| TEXT    | Nombre normalizado para búsqueda         |
| precio       | REAL    | Precio en pesos MXN                      |
| categoria    | TEXT    | Restaurantes, Salud...                   |
| subcategoria | TEXT    | Pizza, Medicamentos...                   |
| fecha        | TEXT    | YYYY-MM-DD                               |
| fuente       | TEXT    | dominos.com.mx, etc.                     |

## Cómo la app Luparte usa estas bases

1. Al instalar la app → descarga `productos.db` y `servicios.db` del release más reciente
2. Cada día → consulta la API de GitHub Releases para comparar la fecha en `version.txt`
3. Si hay versión nueva → descarga las bases en background y reemplaza las locales
4. El buscador de precios consulta las bases localmente (SQLite, sin internet)

## Ejecución manual

```bash
cd pipeline
pip install -r ../requirements.txt
python main.py
```

## Fuentes de datos

| Fuente              | Método                     | Tipo         |
|--------------------|----------------------------|--------------|
| Profeco QQP        | CSV oficial descargado     | Oficial      |
| Walmart.com.mx     | curl_cffi + __NEXT_DATA__  | Scraping     |
| Bodega Aurrerá     | curl_cffi + __NEXT_DATA__  | Scraping     |
| Sam's Club         | curl_cffi + __NEXT_DATA__  | Scraping     |
| Soriana            | Crawl4AI + Playwright      | Scraping     |
| Chedraui           | Crawl4AI + Playwright      | Scraping     |
| La Comer           | Crawl4AI + Playwright      | Scraping     |
| H-E-B              | Crawl4AI                   | Scraping     |
| Steren             | Crawl4AI + Playwright      | Scraping     |
| Liverpool          | Crawl4AI + Playwright      | Scraping     |
| Farmacias GDL      | Crawl4AI + Playwright      | Scraping     |
| Farmacias del Ahorro| Crawl4AI                  | Scraping     |
| Benavides          | Crawl4AI                   | Scraping     |
| Coppel             | Scrapy + Playwright        | Scraping     |
| Domino's México    | Scrapy (API interna JSON)  | Scraping     |
