# ---------------------------------------------------------
# Autor: Camilo Calderon
# Github: @Milo443
# Nota: Desarrollado con amor por Milo
# Mensaje: usa el vibecoding y los agentes responsablemente.
# ---------------------------------------------------------
from .runt import router_runt
from .simit.router import router as router_simit
from .seguridad_vial.router import router as router_consulta_masiva
from .consulta_integral import router_consulta_integral

# Final aggregation of domain routers
# All routers imported here are integrated into main.py
router_runt = router_runt
router_simit = router_simit
router_consulta_masiva = router_consulta_masiva
router_consulta_integral = router_consulta_integral
