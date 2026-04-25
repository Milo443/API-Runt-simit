from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class SimitResponse(BaseModel):
    exito: bool
    data: Optional[Dict[str, Any]] = None
    mensaje: Optional[str] = None
    tiempo_ejecucion: Optional[float] = None
