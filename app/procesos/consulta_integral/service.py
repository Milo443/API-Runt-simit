# ---------------------------------------------------------
# Autor: Camilo Calderon
# Github: @Milo443
# Nota: Desarrollado con amor por Milo
# Mensaje: usa el vibecoding y los agentes responsablemente.
# ---------------------------------------------------------
import asyncio
import time
import random
import httpx
from fastapi import HTTPException
from ..simit.service import SimitService
from ..runt.ciudadano.service import CiudadanoService
from ..runt.vehiculo.service import RuntService
from app.core.logging import logger

class ConsultaIntegralService:
    @staticmethod
    async def run_with_retry(func, *args, max_retries=3, **kwargs):
        """Internal helper to execute a service call with selective retries."""
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                res = await func(*args, **kwargs)
                if res.get("exito"):
                    return res
                last_error = res.get("mensaje") or res.get("error")
                
                # If it's a known 'no data' message, don't retry
                if last_error and ("no existe" in last_error.lower() or "no registra" in last_error.lower()):
                    return res
                
                if attempt < max_retries:
                    delay = 0.5 + random.uniform(0.1, 0.4)
                    logger.warning(f"Retry Attempt {attempt}/{max_retries} for {func.__name__}: {last_error}. Retrying in {round(delay, 1)}s...")
                    await asyncio.sleep(delay)
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries:
                    delay = 0.5 + random.uniform(0.1, 0.4)
                    logger.error(f"Exc in Retry Attempt {attempt}/{max_retries} for {func.__name__}: {last_error}. Retrying in {round(delay, 1)}s...")
                    await asyncio.sleep(delay)
        return {"exito": False, "error": last_error}

    @staticmethod
    async def consultar(
        documento: str, 
        tipo_documento: str = "C",
        placa: str = None,
        identificacion_propietario: str = None
    ) -> dict:
        start_time = time.time()
        
        # Decide which document to use for vehicle consultation
        documento_vehiculo = identificacion_propietario if identificacion_propietario else documento

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            tasks = []
            
            # Task 1: SIMIT (with retries)
            tasks.append(ConsultaIntegralService.run_with_retry(SimitService.consultar_ciudadano, documento, client))
            
            # Task 2: RUNT Ciudadano (with retries)
            tasks.append(ConsultaIntegralService.run_with_retry(CiudadanoService.consultar_ciudadano, tipo_documento, documento, client))
            
            # Task 3: RUNT Vehiculo (Conditional, with retries)
            if placa:
                tasks.append(ConsultaIntegralService.run_with_retry(RuntService.consultar_vehiculo, placa, documento_vehiculo, client))
            else:
                # Add a dummy task that returns None
                async def no_vehiculo(): return {"exito": False, "mensaje": "No se solicitó placa"}
                tasks.append(no_vehiculo())

            # Gather results
            # Note: run_with_retry already handles exceptions, so results will be dicts
            results = await asyncio.gather(*tasks)

            res_simit = results[0]
            res_runt_cit = results[1]
            res_runt_veh = results[2] if placa else None

            return {
                "exito": True,
                "simit": res_simit,
                "runt_ciudadano": res_runt_cit,
                "runt_vehiculo": res_runt_veh,
                "tiempo_ejecucion": round(time.time() - start_time, 2)
            }
