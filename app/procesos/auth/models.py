from pydantic import BaseModel
from typing import Optional, List

class UsuarioActual(BaseModel):
    sub: str
    identificacion: str
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    idroles: Optional[str] = None
    idpantallas: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None

    @property
    def lista_pantallas(self) -> List[str]:
        if not self.idpantallas:
            return []
        return [p.strip() for p in self.idpantallas.split(",")]

    def tiene_acceso_pantalla(self, id_pantalla: str) -> bool:
        return id_pantalla in self.lista_pantallas
