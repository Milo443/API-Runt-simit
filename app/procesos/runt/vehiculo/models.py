from pydantic import BaseModel
from typing import Optional, Any, Dict, List

class VehiculoRequest(BaseModel):
    placa: str
    documento: str

class VehiculoResponse(BaseModel):
    exito: bool
    data: Optional[Dict[str, Any]] = None
    mensaje: Optional[str] = None
    tiempo_ejecucion: Optional[float] = None
