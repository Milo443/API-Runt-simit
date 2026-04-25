# Arquitectura: api-utilidades-ganevirtual

FastAPI pensada para correr tanto en **AWS Lambda** (pruebas) como en **AWS EKS** (producción), con acceso a Oracle R2, Oracle Superflex y PostgreSQL RDS.

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Framework | FastAPI + Uvicorn |
| Lambda adapter | Mangum (`handler = Mangum(app, lifespan="off")`) |
| Oracle | `oracledb` en **thick mode** + SQLAlchemy `QueuePool` |
| PostgreSQL | `psycopg2` + SQLAlchemy `QueuePool` |
| Data processing | Polars (`pl.read_database`) para queries Oracle |
| Concurrencia BD | `ThreadPoolExecutor` global en `DatabaseManager` |
| Settings | Pydantic `BaseSettings` + `.env` |

---

## Estructura de carpetas

```
app/
├── main.py                        # FastAPI app, lifespan, Mangum, CORS, rate limiter
├── core/
│   ├── config.py                  # Settings global (instancia única `settings`)
│   ├── app_metadata.py            # Nombre, versión, tags OpenAPI
│   └── logging.py                 # Configuración de logger
├── db/
│   ├── bd_conections.py           # DatabaseManager — pools, executor, SSH
│   ├── db_configs.py              # Registro de BDs habilitadas
│   ├── database.py                # DatabaseSettings (Pydantic) + defaults pool
│   ├── ssh_tunnel.py              # SSHTunnelManager
│   └── rate_limiter.py            # Middleware rate limiting por IP
└── procesos/
    ├── __init__.py                # Re-exporta todos los routers a main.py
    └── <dominio>/                 # Un dominio por área de negocio
        ├── __init__.py            # Router principal del dominio con prefix
        └── <subdominio>/          # Un subdominio por grupo de endpoints
            ├── __init__.py
            ├── router.py          # Endpoints FastAPI
            ├── service.py         # Lógica de negocio + formateo de respuesta
            ├── queries.py         # SQL, caché, run_in_executor
            ├── models.py          # Enums, Pydantic models, constantes
            ├── docs.py            # Strings OpenAPI y ejemplos de respuesta
            └── sql/               # Archivos .sql cargados al arrancar
                └── consulta_x.sql
```

---

## Flujo de una request

```
HTTP Request
    → RateLimiter (middleware, por IP)
    → Router (router.py) — valida params con FastAPI/Pydantic
    → Service (service.py) — llama queries, formatea respuesta JSON
    → Queries (queries.py) — caché + run_in_executor
        → _sync_query() — ejecuta SQL en hilo del ThreadPoolExecutor
            → Oracle: engine.connect() + pl.read_database()
            → PostgreSQL: engine.connect() + conn.execute()
    ← dict response
```

---

## Patrón de concurrencia (crítico para EKS)

Oracle `thick mode` **no soporta async nativo** — las queries son bloqueantes. Para no bloquear el event loop de FastAPI se usa un `ThreadPoolExecutor` global centralizado en `DatabaseManager`.

```python
# queries.py — patrón estándar para toda query bloqueante
async def get_datos(param: str) -> list:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(DatabaseManager.executor, _sync_query, param)

def _sync_query(param: str) -> list:
    engine = DatabaseManager._get_engine('oracle_r2_produccion')
    with engine.connect() as conn:
        df = pl.read_database(SQL, conn.connection.connection, ...)
    return df.to_dicts()
```

El executor se inicializa en startup con `DB_THREAD_WORKERS` del `.env`:
- **Lambda:** `DB_THREAD_WORKERS=5` (1 request por instancia, el pool no se satura)
- **EKS:** `DB_THREAD_WORKERS=10` (regla: 2× vCPUs del pod)

> **Regla crítica:** `DB_POOL_SIZE + DB_MAX_OVERFLOW >= DB_THREAD_WORKERS`. Si hay más hilos que conexiones, los hilos extra esperan en cola anulando el beneficio.

---

## Patrón de caché en memoria

Caché por proceso/pod. Cada módulo define su propio TTL y lock. Patrón estándar:

```python
# Caché simple (un solo valor global)
_CACHE_TTL      = timedelta(hours=1)
_cache:         list | None = None
_cache_expires: datetime    = datetime.min
_cache_lock     = asyncio.Lock()

async def get_catalogo() -> list:
    global _cache, _cache_expires
    if _cache and datetime.now() < _cache_expires:
        return _cache                           # hit sin lock
    async with _cache_lock:
        if _cache and datetime.now() < _cache_expires:
            return _cache                       # double-check bajo lock
        loop = asyncio.get_running_loop()
        _cache         = await loop.run_in_executor(DatabaseManager.executor, _sync_query)
        _cache_expires = datetime.now() + _CACHE_TTL
    return _cache

# Caché con key compuesta (múltiples combinaciones de parámetros)
_CACHE_TTL  = timedelta(minutes=1)
_cache:      dict = {}                          # key → (data, expires)
_cache_lock  = asyncio.Lock()

async def get_datos(param_a: int, param_b: date) -> list:
    key    = (param_a, param_b)
    cached = _cache.get(key)
    if cached and datetime.now() < cached[1]:
        return cached[0]
    async with _cache_lock:
        cached = _cache.get(key)
        if cached and datetime.now() < cached[1]:
            return cached[0]
        loop   = asyncio.get_running_loop()
        result = await loop.run_in_executor(DatabaseManager.executor, _sync_query, param_a, param_b)
        _cache[key] = (result, datetime.now() + _CACHE_TTL)
    return result
```

TTLs actuales por módulo:

| Endpoint | TTL | Razón |
|---|---|---|
| Catálogo loterias | 1 hora | Raramente cambia |
| Resultados históricos | 1 hora | Nunca cambia |
| Resultados de hoy | 15 min | Pueden llegar sorteos nuevos |
| Productos PAGAMAS | 1 hora | Raramente cambia |
| Números disponibles PAGAMAS | 1 min | Cambian al venderse boletos |

---

## Patrón SQL: enteros vs strings

```python
# Enteros validados → se embeben en el SQL (seguro + Oracle optimiza mejor el plan)
sql = SQL_TEMPLATE.replace("{codigo_bnet}", str(int(codigo_bnet)))

# Strings o fechas → bind params Oracle (evita inyección SQL)
params = {"fecha_sorteo": fecha.strftime('%d/%m/%Y')}
df = pl.read_database(sql, conn, execute_options={"parameters": params})
```

Para strings, los bind params de Oracle se nombran `:nombre`:
```sql
WHERE UPPER(columna) = UPPER(:nombre)
-- múltiples: UPPER(:n0), UPPER(:n1), ...
```

---

## SQL dinámico con filtros opcionales

Para queries con filtros opcionales (lista de códigos, nombres, etc.) se usa `rfind('ORDER BY')` para insertar condiciones `AND` justo antes del `ORDER BY`:

```python
def _build_sql(codigos: list | None, nombres: list | None, params: dict) -> str:
    extras = []
    if codigos:
        vals = ','.join(str(int(c)) for c in codigos)
        extras.append(f"columna IN ({vals})")
    if nombres:
        for i, n in enumerate(nombres):
            params[f'n{i}'] = n.upper()
        extras.append(f"UPPER(col) IN ({','.join(f'UPPER(:n{i})' for i in range(len(nombres)))})")
    if not extras:
        return BASE_SQL
    order_idx = BASE_SQL.upper().rfind('ORDER BY')
    return BASE_SQL[:order_idx] + '\tAND ' + '\n\tAND '.join(extras) + '\n' + BASE_SQL[order_idx:]
```

---

## Cómo agregar un nuevo servicio

### 1. Crear la carpeta del dominio

```
app/procesos/mi_nuevo_dominio/
├── __init__.py           # Router principal del dominio
└── mi_subdominio/
    ├── __init__.py
    ├── router.py
    ├── service.py
    ├── queries.py
    ├── models.py
    ├── docs.py
    └── sql/
        └── consulta_principal.sql
```

### 2. `__init__.py` del dominio

```python
from fastapi import APIRouter

router_mi_dominio = APIRouter(prefix="/mi_dominio", tags=["Mi Dominio"])

from .mi_subdominio.router import router as mi_subdominio_router
router_mi_dominio.include_router(mi_subdominio_router, prefix="/mi_subdominio")
```

### 3. `queries.py` — template completo

```python
import asyncio
import polars as pl
from pathlib import Path
from datetime import date, datetime, timedelta
from app.db.bd_conections import DatabaseManager

_SQL_DIR = Path(__file__).parent / "sql"
_SQL     = (_SQL_DIR / "consulta_principal.sql").read_text(encoding='utf-8').strip().replace(";", "")

# Caché con key compuesta (omitir si el endpoint no necesita caché)
_CACHE_TTL  = timedelta(minutes=5)
_cache:      dict = {}
_cache_lock  = asyncio.Lock()

def _sync_query(param: int, fecha: date) -> list[dict]:
    sql    = _SQL.replace("{param}", str(param))          # entero → embed
    params = {"fecha": fecha.strftime('%d/%m/%Y')}         # string/fecha → bind
    engine = DatabaseManager._get_engine('oracle_r2_produccion')
    with engine.connect() as conn:
        df = pl.read_database(sql, conn.connection.connection,
                              execute_options={"parameters": params},
                              infer_schema_length=None)
    return df.to_dicts()

async def get_datos(param: int, fecha: date) -> list[dict]:
    key    = (param, fecha)
    cached = _cache.get(key)
    if cached and datetime.now() < cached[1]:
        return cached[0]
    async with _cache_lock:
        cached = _cache.get(key)
        if cached and datetime.now() < cached[1]:
            return cached[0]
        loop   = asyncio.get_running_loop()
        result = await loop.run_in_executor(DatabaseManager.executor, _sync_query, param, fecha)
        _cache[key] = (result, datetime.now() + _CACHE_TTL)
    return result
```

### 4. `service.py`

```python
import time
from datetime import date
from fastapi import HTTPException
from . import queries

async def consultar_datos(param: int, fecha: date) -> dict:
    start = time.time()
    try:
        datos = await queries.get_datos(param, fecha)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando Oracle: {str(e)}")
    if not datos:
        raise HTTPException(status_code=404, detail="Sin resultados para los parámetros indicados")
    return {
        "exito":                     True,
        "total":                     len(datos),
        "tiempo_ejecucion_segundos": round(time.time() - start, 3),
        "datos":                     datos,
    }
```

### 5. `router.py`

```python
from datetime import date
from fastapi import APIRouter, Query
from .service import consultar_datos
from .docs import DATOS_DOC, RESPONSES_DATOS
from ..shared.utils import get_fecha_hoy

router = APIRouter()

@router.get("/datos",
            summary="Descripción corta",
            description=DATOS_DOC,
            responses=RESPONSES_DATOS)
async def datos(
    param: int  = Query(..., description="Parámetro obligatorio", example=272),
    fecha: date = Query(None, description="Fecha (YYYY-MM-DD) — por defecto hoy", example=get_fecha_hoy()),
):
    return await consultar_datos(param, fecha or date.today())
```

### 6. Registrar en `app/procesos/__init__.py`

```python
from .mi_nuevo_dominio import router_mi_dominio
router_mi_dominio = router_mi_dominio
```

### 7. Registrar en `app/main.py`

```python
from app.procesos import router_mi_dominio
app.include_router(router_mi_dominio, prefix="/api", tags=["Mi Dominio"])
```

### 8. Agregar el tag en `app/core/app_metadata.py`

```python
{"name": "Mi Dominio", "description": "Descripción del dominio · Caché X minutos"}
```

---

## DatabaseManager

```python
# Obtener engine (para queries en _sync_query)
engine = DatabaseManager._get_engine('oracle_r2_produccion')
engine = DatabaseManager._get_engine('oracle_superflex')
engine = DatabaseManager._get_engine('postgres_ganevirtual')

# Executor global (para run_in_executor en queries.py)
DatabaseManager.executor   # ThreadPoolExecutor, listo tras initialize_pools()

# Schema de una BD
DatabaseManager.get_schema('oracle_r2_produccion')
```

BDs disponibles en `db_configs.py`: `oracle_r2_produccion`, `oracle_superflex`, `postgres_ganevirtual`.

Para agregar una BD nueva:
1. Variables en `.env`
2. Propiedades en `database.py`
3. Entrada en `db_configs.py` con `type`, `url`, `schema`, `name`, `enabled`

---

## Parámetros de tipo lista en query params

FastAPI no acepta listas directamente en `GET`. Patrón usado:

```python
# router.py — recibe como string separado por comas
@router.get("/endpoint")
async def endpoint(codigos: str = Query(None, description="Códigos separados por coma: 1,2,3")):
    lista = [c.strip() for c in codigos.split(",")] if codigos else None
    return await service.consultar(lista)
```

---

## Configuración Lambda ↔ EKS

Ver `DESPLIEGUE.md` en la raíz del proyecto para los valores exactos de `.env` por plataforma y el checklist de migración.

Variables clave por entorno:

| Variable | Lambda | EKS |
|---|---|---|
| `DB_POOL_SIZE` | 1 | 5 |
| `DB_MAX_OVERFLOW` | 1 | 5 |
| `DB_POOL_RECYCLE` | 900 | 300 |
| `DB_THREAD_WORKERS` | 5 | 10 |
| `SSH_TUNNEL_GANEVIRTUAL` | false | false |

---

## Convenciones de código

- **`#!`** — decisión arquitectónica importante, no cambiar sin entender el por qué
- **`#?`** — explicación de un bloque no obvio
- **`#TODO:`** — sección / punto de entrada de una funcionalidad
- `example=` (singular) en `Query()`, nunca `examples=` (plural) — FastAPI OpenAPI
- OpenAPI con fechas dinámicas: `_custom_openapi()` en `main.py` reemplaza fechas de ejemplo en cada request a `/docs`
- SQL cargado al arrancar con `.read_text()` — falla rápido si el archivo no existe (`fail-fast`)
