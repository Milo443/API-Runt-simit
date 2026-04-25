# ---------------------------------------------------------
# Autor: Camilo Calderon
# Github: @Milo443
# Nota: Desarrollado con amor por Milo
# Mensaje: usa el vibecoding y los agentes responsablemente.
# ---------------------------------------------------------
from fastapi import APIRouter, Query, HTTPException
from .service import SimitService
from .models import SimitResponse

router = APIRouter(prefix="/simit", tags=["SIMIT"])

@router.get("/consulta/ciudadano", response_model=SimitResponse)
async def consultar_simit(
    documento: str = Query(..., description="Número de documento para consultar en SIMIT", examples=["1144092903"])
):
    """
    Consulta infracciones, comparendos, multas y acuerdos de pago en el SIMIT.
    Automatiza el desafío Proof-of-Work (CAPTCHA indirecto).
    """
    try:
        resultado = await SimitService.consultar_ciudadano(documento)
        return resultado
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
