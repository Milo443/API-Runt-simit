# ---------------------------------------------------------
# Autor: Camilo Calderon
# Github: @Milo443
# Nota: Desarrollado con amor por Milo
# Mensaje: usa el vibecoding y los agentes responsablemente.
# ---------------------------------------------------------
import jwt
from datetime import datetime
from fastapi import HTTPException, status
from app.core.config import settings
from app.core.logging import logger

JWT_SECRET_KEY = settings.JWT_SECRET_KEY
JWT_ALGORITHM = settings.JWT_ALGORITHM

def decodificar_jwt(token: str) -> dict:
    """
    Decodifica el payload de un token JWT.
    Por defecto, se sigue la lógica de la referencia: 
    - No se verifica firma (opcionalmente activable).
    - Se verifica expiración.
    """
    try:
        # Decodificación inicial para obtener el payload
        # Nota: La referencia indicaba verify_signature: False
        payload = jwt.decode(
            token,
            options={
                "verify_signature": False,  # Siguiendo la referencia del PAU
                "verify_exp": True,
            },
            algorithms=[JWT_ALGORITHM]
        )

        # Verificación manual de expiración si no lo hiciera la librería o para logs detallados
        exp = payload.get("exp")
        if exp:
            exp_date = datetime.fromtimestamp(exp)
            if exp_date < datetime.now():
                logger.warning(f"[AUTH] Token expirado en {exp_date}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expirado"
                )

        return payload

    except jwt.ExpiredSignatureError:
        logger.warning("[AUTH] Token expirado (ExpiredSignatureError)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado"
        )
    except Exception as e:
        logger.error(f"[AUTH] Error decodificando token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )
