from pydantic import BaseModel
from typing import Optional, Dict, Any
from enum import Enum

class TipoDocumentoEnum(str, Enum):
    C = "C" # Cédula de Ciudadanía
    T = "T" # Tarjeta de Identidad
    E = "E" # Cédula de Extranjería
    P = "P" # Pasaporte
    D = "D" # Carné Diplomático
    N = "N" # NIT

class CiudadanoResponse(BaseModel):
    exito: bool
    data: Optional[Dict[str, Any]] = None
    mensaje: Optional[str] = None
    tiempo_ejecucion: Optional[float] = None
