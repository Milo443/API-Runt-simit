# ---------------------------------------------------------
# Autor: Camilo Calderon
# Github: @Milo443
# Nota: Desarrollado con amor por Milo
# Mensaje: usa el vibecoding y los agentes responsablemente.
# ---------------------------------------------------------
import httpx
import base64
import time
import asyncio
import pytesseract
import numpy as np
import cv2
from fastapi import HTTPException
from app.core.config import settings
from app.core.logging import logger

# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

# Constants for RUNT Citizen API
CIUDADANO_API_BASE = settings.RUNT_CIUDADANO_API_BASE
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "x-funcionalidad": "SHELL",
    "Origin": "https://portalpublico.runt.gov.co",
    "Referer": "https://portalpublico.runt.gov.co/",
    "Content-Type": "application/json"
}

class CiudadanoService:
    # No static initialization needed for pytesseract as it's a wrapper

    @classmethod
    async def get_captcha(cls, client: httpx.AsyncClient):
        """Fetches a new citizen captcha from RUNT API."""
        url = f"{CIUDADANO_API_BASE}/captcha/libre-captcha/generar"
        try:
            response = await client.get(url, headers=HEADERS)
            response.raise_for_status()
            data = response.json()
            return data.get("id"), data.get("imagen")
        except Exception as e:
            logger.error(f"Error fetching citizen captcha: {e}")
            raise HTTPException(status_code=502, detail="No se pudo obtener el captcha de ciudadano")

    @classmethod
    def solve_captcha(cls, base64_img: str) -> str:
        """Solves the base64 captcha image using pytesseract."""
        if not base64_img:
            return ""
        try:
            # 1. Strip prefix and decode
            if "," in base64_img:
                base64_img = base64_img.split(",")[1]
            missing_padding = len(base64_img) % 4
            if missing_padding:
                base64_img += '=' * (4 - missing_padding)
            img_bytes = base64.b64decode(base64_img)

            # 2. Preprocess image for Tesseract
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Upscale image slightly to help Tesseract (reduced from 2x to 1.2x for CPU optimization)
            gray = cv2.resize(gray, None, fx=1.2, fy=1.2, interpolation=cv2.INTER_CUBIC)
            
            # Thresholding to remove noise
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
            
            # psm 7: Treat the image as a single text line.
            custom_config = r'--oem 3 --psm 7'
            captcha_text = pytesseract.image_to_string(thresh, config=custom_config)
            
            # Clean text
            captcha_text = "".join(filter(str.isalnum, captcha_text)).strip()
            
            logger.info(f"Citizen CAPTCHA solved (pytesseract): {captcha_text}")
            return captcha_text
        except Exception as e:
            logger.error(f"Error solving citizen captcha: {e}")
            return ""

    @classmethod
    async def consultar_ciudadano(cls, tipo_documento: str, documento: str, client: httpx.AsyncClient = None) -> dict:
        """Main flow to consult citizen information."""
        start_time = time.time()
        
        # Decide whether to use provided client or create a temporary one
        own_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
            own_client = True
            
        try:
            token = None
            citizen_info = {}
            max_attempts = 5
            
            for attempt in range(1, max_attempts + 1):
                logger.info(f"Citizen Auth Attempt {attempt}/{max_attempts}")
                
                # 1. Get and solve CAPTCHA
                id_captcha, img_base64 = await cls.get_captcha(client)
                
                # Run CPU-bound captcha solving in executor
                loop = asyncio.get_event_loop()
                solved_text = await loop.run_in_executor(None, cls.solve_captcha, img_base64)
                
                if not solved_text or len(solved_text) != 5:
                    logger.warning(f"Attempt {attempt}: Bad captcha solve length, retrying...")
                    continue

                # 2. Authenticate
                auth_url = f"{CIUDADANO_API_BASE}/auth"
                payload = {
                    "tipoDocumento": tipo_documento.upper(),
                    "documento": documento,
                    "reCaptcha": None,
                    "captcha": solved_text,
                    "valueCaptchaEncripted": "",
                    "idLibreCaptcha": id_captcha,
                    "noDocumento": documento
                }
                
                try:
                    resp = await client.post(auth_url, json=payload, headers=HEADERS)
                    if resp.status_code == 200:
                        data = resp.json()
                        token = resp.headers.get("Auth-Token") or data.get("token")
                        citizen_info = data
                        if token:
                            logger.info(f"Citizen Auth Success on attempt {attempt}")
                            break
                    else:
                        logger.warning(f"Attempt {attempt} failed: {resp.status_code} - {resp.text}")
                except Exception as e:
                    logger.error(f"Error during Auth attempt {attempt}: {e}")
                
                if attempt < max_attempts:
                    await asyncio.sleep(0.5)

            if not token:
                raise HTTPException(status_code=401, detail="No se pudo autenticar ciudadano tras 5 intentos")

            # 3. Fetch Licenses
            data_headers = HEADERS.copy()
            data_headers["Auth-Token"] = token if "Bearer" in token else f"Bearer {token}"
            
            lic_url = f"{CIUDADANO_API_BASE}/consulta-ciudadano/licencias"
            lic_resp = await client.get(lic_url, headers=data_headers)
            lic_resp.raise_for_status()
            lic_data = lic_resp.json()
            if not isinstance(lic_data, list):
                lic_data = []
            
            # 100% Parity: Flatten nested categories and aggregate restrictions
            flattened_lics = []
            all_restrictions = []
            
            for lic in lic_data:
                if isinstance(lic, dict):
                    # Aggregate restrictions from each license header
                    rst = lic.get("restricciones")
                    if rst and rst.strip() and rst.strip().upper() != "NINGUNA":
                        all_restrictions.append(rst.strip())
                    
                    # Process nested categories (detalleLicencia)
                    cats = lic.get("detalleLicencia", [])
                    if isinstance(cats, list):
                        for cat in cats:
                            if isinstance(cat, dict):
                                # Copy all fields from category and add header context
                                record = cat.copy()
                                record.update({
                                    "numeroLicencia": lic.get("numeroLicencia"),
                                    "estadoLicenciaHeader": lic.get("estadoLicencia"),
                                    "otExpide": lic.get("otExpide")
                                })
                                flattened_lics.append(record)

            # Standardize citizen info summary (metadata only)
            citizen_summary = citizen_info.get("personaResumenDTO", citizen_info)
            logger.debug(f"Citizen Summary for {documento}: {str(citizen_summary)[:200]}...")
            
            # DERIVATION RULE: Obtain status EXCLUSIVELY from the licenses list (endpoint /licencias)
            # and NOT from the 'auth' summary as per user request.
            general_state = "SIN LICENCIA"
            if lic_data:
                # Logic: If any record is ACTIVA, the status is Vigente. 
                # Otherwise, take the status of the first record (most recent).
                all_states = [str(l.get("estadoLicencia", "")).upper() for l in lic_data if isinstance(l, dict)]
                if "ACTIVA" in all_states:
                    general_state = "Vigente"
                elif all_states:
                    # Find the first non-empty status
                    valid_states = [s for s in all_states if s and s != "NONE"]
                    state = valid_states[0] if valid_states else "DESCONOCIDO"
                    general_state = "Vigente" if state == "ACTIVA" else state
            
            # Use unique set for restrictions
            unique_restrictions = sorted(list(set(all_restrictions)))
            
            return {
                "exito": True,
                "data": {
                    "detalleLicencia": flattened_lics,
                    "estadoLicencia": general_state,
                    "restricciones": "\n".join(unique_restrictions) if unique_restrictions else ""
                },
                "tiempo_ejecucion": round(time.time() - start_time, 2)
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"RUNT Citizen API Error: {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail="Error en la comunicación con RUNT")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Internal Error in Citizen Service: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            if own_client:
                await client.aclose()
