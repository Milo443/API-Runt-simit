# ---------------------------------------------------------
# Autor: Camilo Calderon
# Github: @Milo443
# Nota: Desarrollado con amor por Milo
# Mensaje: usa el vibecoding y los agentes responsablemente.
# ---------------------------------------------------------
from fastapi import APIRouter, UploadFile, File, Query, Response, Depends, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from .service import SeguridadVialService
from .models import ProcessRequest
from app.core.config import settings
from app.procesos.auth import require_pantalla, get_usuario_actual, UsuarioActual
import io
import os

router = APIRouter(prefix="/consulta-masiva", tags=["Consulta Masiva"])

@router.post("/procesar-excel",
             summary="Procesar Excel de Consulta Masiva",
             description="Carga un archivo Excel, aplica filtros e inicia el proceso en segundo plano.")
async def procesar_excel(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Archivo Excel (.xlsx)"),
    es_conductor_laboral: str = Query("si", description="Filtrar por columna 'Es Conductor Laboral' (si/no)", examples=["si"]),
    rodamiento: str = Query("si", description="Filtrar por columna 'Rodamiento' (si/no)", examples=["si"]),
    client_id: str = Query(None, description="ID único para notificaciones en tiempo real vía WebSocket"),
    usuario: UsuarioActual = Depends(require_pantalla(settings.SCREEN_ID_MASIVA))
):
    """
    Endpoint that receives an Excel file and starts background processing.
    """
    if not client_id:
        raise HTTPException(status_code=400, detail="client_id is required for mass processing tracking")

    content = await file.read()
    
    # Run in background
    background_tasks.add_task(
        SeguridadVialService.procesar_excel, 
        content, 
        es_conductor_laboral, 
        rodamiento, 
        client_id, 
        usuario.identificacion
    )
    
    # Also clean up old tasks periodically (could be moved to a scheduler but this is simple)
    background_tasks.add_task(SeguridadVialService.cleanup_old_tasks)

    return {
        "status": "processing",
        "message": "El archivo se está procesando en segundo plano.",
        "client_id": client_id
    }

@router.get("/status/{client_id}", summary="Consultar estado del proceso")
async def get_status(
    client_id: str,
    usuario: UsuarioActual = Depends(require_pantalla(settings.SCREEN_ID_MASIVA))
):
    status_data = await SeguridadVialService.get_task_status(client_id, usuario.identificacion)
    if not status_data:
        raise HTTPException(status_code=404, detail="Proceso no encontrado o no pertenece al usuario")
    
    return status_data

@router.get("/download/{client_id}", summary="Descargar resultado del proceso")
async def download_result(
    client_id: str,
    usuario: UsuarioActual = Depends(require_pantalla(settings.SCREEN_ID_MASIVA))
):
    status_data = await SeguridadVialService.get_task_status(client_id, usuario.identificacion)
    if not status_data:
        raise HTTPException(status_code=404, detail="Proceso no encontrado o no pertenece al usuario")
    
    if not status_data.get("result_ready"):
        raise HTTPException(status_code=400, detail="El resultado aún no está listo")

    file_path = SeguridadVialService._get_result_path(client_id)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado en el servidor")

    return FileResponse(
        path=file_path,
        filename=f"Resultado_Seguridad_Vial_{client_id}.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
