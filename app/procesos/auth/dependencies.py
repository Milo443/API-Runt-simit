# ---------------------------------------------------------
# Autor: Camilo Calderon
# Github: @Milo443
# Nota: Desarrollado con amor por Milo
# Mensaje: usa el vibecoding y los agentes responsablemente.
# ---------------------------------------------------------
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from .service import decodificar_jwt
from .models import UsuarioActual

security = HTTPBearer()

async def get_usuario_actual(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UsuarioActual:
    """
    Dependencia que extrae y valida el usuario desde el header Authorization.
    FastAPI HTTPBearer ya valida que sea un esquema Bearer.
    """
    token = credentials.credentials
    payload = decodificar_jwt(token)
    
    return UsuarioActual(**payload)

def require_pantalla(id_pantalla: str):
    """
    Dependencia de factoría para exigir acceso a una pantalla específica.
    """
    async def dependencia_acceso(
        usuario: UsuarioActual = Depends(get_usuario_actual)
    ) -> UsuarioActual:
        if not usuario.tiene_acceso_pantalla(id_pantalla):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tienes acceso a la pantalla requerida ({id_pantalla})"
            )
        return usuario
    
    return dependencia_acceso
