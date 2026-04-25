from pydantic import BaseModel
from typing import Optional, Dict, Any
from ..runt.ciudadano.models import TipoDocumentoEnum

class ConsultaIntegralResponse(BaseModel):
    exito: bool
    runt_ciudadano: Optional[Dict[str, Any]] = None
    runt_vehiculo: Optional[Dict[str, Any]] = None
    simit: Optional[Dict[str, Any]] = None
    tiempo_ejecucion: Optional[float] = None
    mensaje: Optional[str] = None
