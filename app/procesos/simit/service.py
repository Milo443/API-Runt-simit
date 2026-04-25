# ---------------------------------------------------------
# Autor: Camilo Calderon
# Github: @Milo443
# Nota: Desarrollado con amor por Milo
# Mensaje: usa el vibecoding y los agentes responsablemente.
# ---------------------------------------------------------
import httpx
import time
import json
import asyncio
from .utils import solve_pow
from fastapi import HTTPException
from app.core.config import settings
from app.core.logging import logger

# Constants for SIMIT API
SIMIT_API_BASE = settings.SIMIT_API_BASE
CAPTCHA_API = settings.SIMIT_CAPTCHA_API

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "es-ES,es;q=0.9",
    "Connection": "keep-alive",
    "Content-Type": "application/json",
    "Origin": "https://www.fcm.org.co",
    "Referer": "https://www.fcm.org.co/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Priority": "u=1, i"
}

class SimitService:
    @classmethod
    async def get_captcha_challenge(cls, client: httpx.AsyncClient):
        """Fetches the Proof-of-Work challenge from the qxCaptcha API."""
        try:
            # The API expects multipart/form-data for the question endpoint
            resp = await client.post(
                CAPTCHA_API, 
                data={"endpoint": "question"}, 
                headers={
                    "User-Agent": HEADERS["User-Agent"],
                    "Origin": HEADERS["Origin"],
                    "Referer": HEADERS["Referer"],
                    "Accept": "*/*"
                },
                timeout=15.0
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("error"):
                logger.error(f"qxCaptcha API returned error: {data}")
                raise Exception("Error in qxCaptcha challenge retrieval")
            
            return data["data"]["question"], data["data"]["recommended_difficulty"], resp.cookies
        except Exception as e:
            logger.error(f"Error fetching SIMIT captcha: {e}")
            raise HTTPException(status_code=502, detail="No se pudo obtener el desafío de seguridad (CAPTCHA) de SIMIT")

    @classmethod
    async def consultar_ciudadano(cls, documento: str, client: httpx.AsyncClient = None) -> dict:
        """
        Main entry point for SIMIT consultation.
        Automates the PoW solving process and retrieves infractions/fines.
        Includes a retry mechanism (up to 3 attempts).
        """
        max_attempts = 3
        last_exception = None
        
        for attempt in range(1, max_attempts + 1):
            start_time = time.time()
            own_client = False
            current_client = client
            
            try:
                if current_client is None:
                    current_client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
                    own_client = True
                
                # 1. Obtain Challenge
                logger.info(f"Attempt {attempt}/{max_attempts}: Fetching SIMIT PoW challenge...")
                question, difficulty, captcha_cookies = await cls.get_captcha_challenge(current_client)
                
                # 2. Solve Challenge (Synchronous computation)
                logger.info(f"Attempt {attempt}/{max_attempts}: Solving challenge (Difficulty: {difficulty})...")
                pow_time = int(time.time())
                
                loop = asyncio.get_event_loop()
                pow_solutions = await loop.run_in_executor(None, solve_pow, question, difficulty, pow_time)
                
                # 3. Perform Consultation
                logger.info(f"Attempt {attempt}/{max_attempts}: Querying SIMIT account status for {documento}...")
                consult_url = f"{SIMIT_API_BASE}/estadocuenta/consulta"
                
                payload = {
                    "filtro": str(documento),
                    "reCaptchaDTO": {
                        "response": json.dumps(pow_solutions[:1], separators=(',', ':')),
                        "consumidor": "1"
                    }
                }
                
                resp = await current_client.post(consult_url, json=payload, headers=HEADERS, cookies=captcha_cookies)
                
                if resp.status_code != 200:
                    logger.error(f"SIMIT Attempt {attempt} Failed: {resp.status_code} - {resp.text}")
                    if resp.status_code == 401:
                        raise HTTPException(status_code=401, detail=f"SIMIT rechazo el token de seguridad: {resp.json().get('descripcion')}")
                    raise HTTPException(status_code=resp.status_code, detail="Error al consultar infracciones en SIMIT")
                
                raw_data = resp.json()
                logger.info(f"SIMIT RAW DATA: {json.dumps(raw_data)[:500]}...")
                
                # Standardize according to diccionario.txt
                comp = raw_data.get("comparendos", []) if isinstance(raw_data.get("comparendos"), list) else []
                reso = raw_data.get("resoluciones", []) if isinstance(raw_data.get("resoluciones"), list) else []
                multas = raw_data.get("multas", []) if isinstance(raw_data.get("multas"), list) else []
                acuerdos = raw_data.get("acuerdosPago", []) if isinstance(raw_data.get("acuerdosPago"), list) else []
                
                for item in comp: item["tipoItem"] = "Comparendo"
                for item in reso: item["tipoItem"] = "Resolución"
                for item in multas: item["tipoItem"] = "Multa"
                for item in acuerdos: item["tipoItem"] = "Acuerdo de Pago"
                
                standardized_items = []
                for item in (comp + reso + multas + acuerdos):
                    if isinstance(item, dict):
                        enriched_item = item.copy()
                        enriched_item.update({
                            "codigoInfraccion": item.get("infraccion") or item.get("codigoInfraccion"),
                            "descripcionInfraccion": item.get("descripcionInfraccion") or item.get("infraccion"),
                            "fechaImposicion": item.get("fecha") or item.get("fechaImposicion"),
                            "estado": item.get("estado"),
                        })
                        standardized_items.append(enriched_item)
                
                return {
                    "exito": True,
                    "data": {
                        "infracciones": standardized_items
                    },
                    "tiempo_ejecucion": round(time.time() - start_time, 2),
                    "intentos": attempt
                }

            except (httpx.HTTPError, HTTPException, Exception) as e:
                last_exception = e
                logger.warning(f"SIMIT Attempt {attempt} failed for {documento}: {str(e)}")
                if attempt < max_attempts:
                    wait_time = 1.5  # Fixed delay
                    await asyncio.sleep(wait_time)
                continue
            finally:
                if own_client:
                    await current_client.aclose()
        
        # If all attempts failed
        logger.error(f"SIMIT query failed after {max_attempts} attempts for {documento}")
        if isinstance(last_exception, HTTPException):
            raise last_exception
        raise HTTPException(status_code=500, detail=f"SIMIT temporalmente fuera de servicio tras {max_attempts} reintentos")

