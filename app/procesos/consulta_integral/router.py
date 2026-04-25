# ---------------------------------------------------------
# Autor: Camilo Calderon
# Github: @Milo443
# Nota: Desarrollado con amor por Milo
# Mensaje: usa el vibecoding y los agentes responsablemente.
# ---------------------------------------------------------
from fastapi import APIRouter, Query, HTTPException, Depends
from .service import ConsultaIntegralService
from .models import ConsultaIntegralResponse, TipoDocumentoEnum
from app.core.config import settings
from app.procesos.auth import require_pantalla

router = APIRouter(prefix="/consulta-integral", tags=["Consulta Integral"])

@router.get("/ciudadano", response_model=ConsultaIntegralResponse, summary="Consulta Individual Ciudadano/Vehículo")
async def consultar_integral(
    documento: str = Query(..., description="Número de identificación del ciudadano a consultar.", examples=["1143875074"]),
    tipoDocumento: TipoDocumentoEnum = Query(TipoDocumentoEnum.C, description="Tipo de identificación (C=Cédula, T=Tarjeta Identidad, etc.)"),
    placa: str = Query(None, description="Placa del vehículo (opcional, activa consulta de vehículo)", examples=["MXT123"]),
    identificacionPropietario: str = Query(None, description="Identificación del propietario (opcional). Si se omite, se asume el 'documento' principal."),
    _auth = Depends(require_pantalla(settings.SCREEN_ID_INDIVIDUAL))
):
    """
    Consulta integral que unifica SIMIT, RUNT Ciudadano y RUNT Vehículo.
    """
    try:
        resultado = await ConsultaIntegralService.consultar(
            documento=documento,
            tipo_documento=tipoDocumento,
            placa=placa,
            identificacion_propietario=identificacionPropietario
        )
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
