# ---------------------------------------------------------
# Autor: Camilo Calderon
# Github: @Milo443
# Nota: Desarrollado con amor por Milo
# Mensaje: usa el vibecoding y los agentes responsablemente.
# ---------------------------------------------------------
from datetime import date
from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any
from .service import RuntService
from .models import VehiculoResponse

router = APIRouter()

@router.get("/vehiculo",
            summary="Consulta Vehículo Real",
            description="Consulta información técnica de un vehículo directamente desde RUNT (automatizando CAPTCHA).",
            response_model=VehiculoResponse,
            tags=["RUNT"])
async def get_real_vehiculo(
    placa: str = Query(..., description="Placa del vehículo", examples=["MXT123"]),
    documento: str = Query(..., description="Cédula del propietario", examples=["12345678"]),
):
    try:
        return await RuntService.consultar_vehiculo(placa, documento)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")
