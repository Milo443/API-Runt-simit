# Guía de Integración: Base de Datos para Seguridad Vial

Esta guía detalla el proceso técnico para migrar el módulo de **Seguridad Vial** desde una arquitectura basada en archivos Excel a un flujo de trabajo integrado con bases de datos relacionales (Oracle/PostgreSQL).

---

## 1. Cambio de Paradigma: De Archivo a Registros SQL

En el modelo actual, la entrada es un `bytes` proveniente de un `UploadFile`. En la integración futura, la entrada será un conjunto de registros pendientes en una tabla de base de datos.

### Esquema Sugerido (Tablas de Control)

#### Tabla `SVC_SOLICITUDES_PROCESAMIENTO`
| Columna | Tipo | Descripción |
|---|---|---|
| `ID_SOLICITUD` | `INT` (PK) | Identificador único de la fila. |
| `CEDULA` | `VARCHAR` | Documento de identidad del conductor. |
| `NOMBRE` | `VARCHAR` | Nombre completo del conductor. |
| `PLACA` | `VARCHAR` | Placa del vehículo a consultar. |
| `CATEGORIA_LABOR` | `VARCHAR` | Categoría requerida para el contrato laboral. |
| `ESTADO` | `VARCHAR` | `PND` (Pendiente), `PRG` (En progreso), `OK` (Exitoso), `ERR` (Fallido). |
| `FECHA_SOLICITUD` | `TIMESTAMP` | Fecha de creación del registro. |
| `FECHA_PROCESAMIENTO` | `TIMESTAMP` | Fecha en la que se completó el servicio. |
| `CLIENT_ID_WS` | `VARCHAR` | ID de WebSocket para notificaciones en tiempo real. |

---

## 2. Nueva Capa de Consultas (`queries.py`)

Siguiendo el patrón definido en `ARQUITECTURA.md`, se debe crear un archivo `app/procesos/seguridad_vial/queries.py` para manejar la interacción con la base de datos de manera segura y eficiente (especialmente para Oracle).

```python
import asyncio
import polars as pl
from datetime import datetime
from app.db.bd_conections import DatabaseManager

def _get_pendientes_sync() -> list[dict]:
    """Consulta síncrona para obtener registros en estado PND."""
    sql = "SELECT * FROM SVC_SOLICITUDES_PROCESAMIENTO WHERE ESTADO = 'PND'"
    # Se utiliza el engine de Oracle definido en DatabaseManager
    engine = DatabaseManager._get_engine('oracle_r2_produccion')
    with engine.connect() as conn:
        df = pl.read_database(sql, conn.connection.connection)
    return df.to_dicts()

async def get_solicitudes_pendientes() -> list[dict]:
    """Envoltura asíncrona usando el ThreadPoolExecutor global."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(DatabaseManager.executor, _get_pendientes_sync)

def _update_resultado_sync(id_solicitud: int, estado: str, data_json: str):
    """Actualiza e inserta el resultado procesado."""
    sql = """
        UPDATE SVC_SOLICITUDES_PROCESAMIENTO 
        SET ESTADO = :estado, FECHA_PROCESAMIENTO = :fecha 
        WHERE ID_SOLICITUD = :id
    """
    params = {
        "estado": estado,
        "fecha": datetime.now(),
        "id": id_solicitud
    }
    engine = DatabaseManager._get_engine('oracle_r2_produccion')
    with engine.connect() as conn:
        conn.execute(sql, params)
        # Aquí también podrías insertar los resultados detallados en una tabla de 'RESULTADOS'
```

---

## 3. Refactorización del Servicio (`service.py`)

El método `procesar_excel` se divide o reemplaza por `procesar_desde_db`. La lógica de consulta a RUNT/SIMIT se mantiene igual, pero el bucle de procesamiento cambia.

### Estructura Propuesta

```python
class SeguridadVialService:
    @staticmethod
    async def procesar_desde_db():
        """
        Consulta registros PND desde la base de datos y los procesa concurrentemente.
        """
        # 1. Obtener registros pendientes
        pendientes = await queries.get_solicitudes_pendientes()
        if not pendientes:
            return 0
            
        # 2. Configuración de procesamiento concurrente (Semáforo)
        semaphore = asyncio.Semaphore(settings.BATCH_SIZE)
        
        async def procesar_fila(fila, client):
            async with semaphore:
                # Lógica de consulta (RuntService, SimitService)
                # Esta lógica ya existe en procesar_excel()
                res_veh = await RuntService.consultar_vehiculo(fila['PLACA'], ...)
                res_cit = await CiudadanoService.consultar_ciudadano(...)
                
                # ... (Procesamiento de datos y mapeo) ...
                
                # 3. Notificar vía WebSocket si hay un CLIENT_ID
                if fila.get('CLIENT_ID_WS'):
                    await manager.send_personal_message({
                        "id": fila['ID_SOLICITUD'],
                        "status": "finalizado",
                        "cedula": fila['CEDULA']
                    }, fila['CLIENT_ID_WS'])
                
                # 4. Persistir en Base de Datos
                await queries.update_resultado_solicitud(fila['ID_SOLICITUD'], "OK", ...)

        # Ejecución en lote controlado
        async with httpx.AsyncClient(...) as client:
            tasks = [procesar_fila(f, client) for f in pendientes]
            await asyncio.gather(*tasks)
            
        return len(pendientes)
```

---

## 4. Nuevo Punto de Entrada en el API (`router.py`)

Se añade un endpoint que dispare el proceso. Este puede ser ejecutado manualmente o mediante un trigger externo (WebHook o Job de base de datos).

```python
@router.post("/disparar-procesamiento-db", 
             summary="Inicia el procesamiento de la cola en base de datos")
async def disparar_db():
    total_procesados = await SeguridadVialService.procesar_desde_db()
    return {"exito": True, "total": total_procesados}
```

> [!TIP]
> Para sistemas de alta disponibilidad, se recomienda mover este procesamiento a un **Background Task** de FastAPI para liberar la respuesta HTTP inmediatamente.

---

## 5. Ventajas de esta Integración

1.  **Trazabilidad**: Cada registro tiene un ID único en base de datos, facilitando auditorías.
2.  **Reprocesamiento**: Si una consulta falla (ej: CAPTCHA no resuelto), el estado puede cambiar de `ERR` a `PND` automáticamente para un segundo intento.
3.  **Persistencia**: Los datos no se pierden si el servidor se reinicia, a diferencia de un stream de archivo en memoria.
4.  **Escalabilidad**: Múltiples instancias del API pueden consultar la tabla de "Pendientes" (usando `FOR UPDATE SKIP LOCKED` en SQL) para procesar miles de registros en paralelo.

---

### Conclusión
La migración es directa debido a que la lógica de negocio (RUNT/SIMIT) ya está encapsulada en sus respectivos servicios. El cambio principal radica en la **fuente de datos** (sustituir el bucle de `in_ws.cell` por un bucle sobre una lista de diccionarios SQL/Polars) y la **persistencia** (sustituir `out_ws.cell` por llamadas a `queries.py`).
