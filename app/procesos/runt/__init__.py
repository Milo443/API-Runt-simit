from fastapi import APIRouter

# Creating the domain router
router_runt = APIRouter(prefix="/runt", tags=["RUNT"])

# Inclusion of sub-domain routers
from .vehiculo.router import router as vehiculo_router
from .ciudadano.router import router as ciudadano_router

# Each sub-domain router is included with its own prefix
# This achieves the path: /api/runt/consulta/vehiculo and /api/runt/consulta/ciudadano
router_runt.include_router(vehiculo_router, prefix="/consulta")
router_runt.include_router(ciudadano_router, prefix="/consulta")
