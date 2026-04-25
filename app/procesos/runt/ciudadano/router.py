# ---------------------------------------------------------
# Autor: Camilo Calderon
# Github: @Milo443
# Nota: Desarrollado con amor por Milo
# Mensaje: usa el vibecoding y los agentes responsablemente.
# ---------------------------------------------------------
from fastapi import APIRouter, Query, HTTPException
from .service import CiudadanoService
from .models import CiudadanoResponse, TipoDocumentoEnum

router = APIRouter()

@router.get("/ciudadano", response_model=CiudadanoResponse, tags=["RUNT"])
async def consultar_ciudadano(
    tipoDocumento: TipoDocumentoEnum = Query(..., description="Tipo de documento (C, T, E, P, etc.)"),
    documento: str = Query(..., description="Número de documento", examples=["1143875074"])
):
    """
    Consulta información de un ciudadano en el RUNT (Licencias, etc.).
    """
    try:
        resultado = await CiudadanoService.consultar_ciudadano(tipoDocumento, documento)
        return resultado
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
