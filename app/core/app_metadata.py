# ---------------------------------------------------------
# Autor: Camilo Calderon
# Github: @Milo443
# Nota: Desarrollado con amor por Milo
# Mensaje: usa el vibecoding y los agentes responsablemente.
# ---------------------------------------------------------
from .config import settings

APP_TITLE = settings.APP_NAME
APP_VERSION = settings.VERSION
APP_DESCRIPTION = """
API Orquestadora para el sistema RUNT.
Diseño basado en arquitectura escalable para AWS Lambda y EKS.
"""

TAGS_METADATA = [
    {
        "name": "Consulta Integral",
        "description": "Orquestación de RUNT y SIMIT para consultas individuales.",
    },
    {
        "name": "Consulta Masiva",
        "description": "Procesamiento masivo de datos mediante archivos Excel.",
    },
    {
        "name": "RUNT",
        "description": "Acceso directo a servicios del RUNT (Ciudadano y Vehículo).",
    },
    {
        "name": "SIMIT",
        "description": "Consulta de infracciones y multas (Federación Colombiana de Municipios).",
    },
    {
        "name": "Sistema",
        "description": "Endpoints de control, salud y utilidades de la API.",
    },
]

# Detailed metadata for ReDoc
TAGS_METADATA_RICH = [
    {
        "name": "Consulta Integral",
        "description": """
### Orquestador Individual
Unifica la información de múltiples fuentes en una sola respuesta.
- **RUNT Ciudadano**: Datos básicos y licencias.
- **RUNT Vehículo**: Información técnica y gravámenes.
- **SIMIT**: Infracciones y acuerdos de pago.
""",
    },
    {
        "name": "Consulta Masiva",
        "description": """
### Orquestador Masivo
Diseñado para el procesamiento de grandes volúmenes de datos cargados vía Excel.
- Aplica filtros de negocio (Conductor Laboral, Rodamiento).
- Notifica progreso vía WebSockets.
- Genera un archivo Excel de salida con la información consolidada.
""",
    },
    {
        "name": "RUNT",
        "description": "Servicios de consulta directa a la base de datos central del RUNT. Incluye caché de 15 minutos.",
    },
    {
        "name": "SIMIT",
        "description": """
### Integración con SIMIT (qxCaptcha)
Consultas de infracciones y acuerdos de pago.

#### Funcionamiento de qxCaptcha (PoW)
SIMIT utiliza **qxCaptcha** para prevenir bots. Este sistema requiere:
1. **Desafío**: Obtención de token y dificultad.
2. **Cálculo**: Resolución de un hash SHA256 con prefijo específico (PoW).
3. **Mantenimiento**: Gestión de cookies de sesión WAF (`ADC_CONN_*`).

*Nota: El proceso demora ~2 segundos debido al costo computacional del hash.*
""",
    },
    {
        "name": "Sistema",
        "description": "Herramientas administrativas, monitoreo de salud (Healthcheck) y gestión de WebSocket.",
    },
]
