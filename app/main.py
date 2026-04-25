# ---------------------------------------------------------
# Autor: Camilo Calderon
# Github: @Milo443
# Nota: Desarrollado con amor por Milo
# Mensaje: usa el vibecoding y los agentes responsablemente.
# ---------------------------------------------------------
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi

from app.core.config import settings
from app.core.app_metadata import APP_TITLE, APP_VERSION, APP_DESCRIPTION, TAGS_METADATA, TAGS_METADATA_RICH
from app.procesos import router_runt, router_simit, router_consulta_masiva, router_consulta_integral
from app.core.websocket_manager import manager
from app.procesos.auth import get_usuario_actual, require_pantalla

# FastAPI instance
app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    docs_url=None,   # Deshabilitados para control manual
    redoc_url=None,
    openapi_url=None # Deshabilitado el por defecto
)

# --- Custom OpenAPI Endpoints ---

@app.get("/openapi.json", include_in_schema=False)
async def openapi_concise():
    """Esquema OpenAPI para Swagger (Descripciones cortas)"""
    return get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=TAGS_METADATA
    )

@app.get("/openapi_rich.json", include_in_schema=False)
async def openapi_detailed():
    """Esquema OpenAPI para ReDoc (Descripciones largas y técnicas)"""
    return get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=TAGS_METADATA_RICH
    )

# --- Documentation Routes ---

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=app.title + " - Interactive Docs",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )

@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url="/openapi_rich.json",
        title=app.title + " - Detailed Documentation",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.1.3/bundles/redoc.standalone.js",
    )

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # joan no te olvides habilitar cors para pau demo
)

# Inclusion of all business domain routers
# All routes are protected with valid JWT as a baseline
app.include_router(router_runt, prefix="/api", dependencies=[Depends(get_usuario_actual)])
app.include_router(router_simit, prefix="/api", dependencies=[Depends(get_usuario_actual)])

# Orchestrators have specific screen ID requirements
app.include_router(router_consulta_masiva, prefix="/api", dependencies=[Depends(require_pantalla(settings.SCREEN_ID_MASIVA))])
app.include_router(router_consulta_integral, prefix="/api", dependencies=[Depends(require_pantalla(settings.SCREEN_ID_INDIVIDUAL))])

@app.get("/", tags=["Sistema"])
async def root():
    return {
        "app": APP_TITLE,
        "version": APP_VERSION,
        "status": "Running",
        "api_docs": "/docs"
    }

# AWS Lambda Handler
handler = Mangum(app, lifespan="off")

# WebSocket Endpoint
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(client_id, websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(client_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
