# ---------------------------------------------------------
# Autor: Camilo Calderon
# Github: @Milo443
# Nota: Desarrollado con amor por Milo
# Mensaje: usa el vibecoding y los agentes responsablemente.
# ---------------------------------------------------------
import httpx
import base64
import time
import io
import asyncio
import pytesseract
import numpy as np
import cv2
from datetime import datetime
from PIL import Image
from fastapi import HTTPException
from app.core.config import settings
from app.core.logging import logger

# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

# Constants for RUNT API
RUNT_API_BASE = settings.RUNT_VEHICULO_API_BASE
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "x-funcionalidad": "SHELL",
    "Origin": "https://portalpublico.runt.gov.co",
    "Referer": "https://portalpublico.runt.gov.co/",
    "Content-Type": "application/json"
}

class RuntService:
    # No static initialization needed for pytesseract as it's a wrapper

    @staticmethod
    async def get_captcha(client: httpx.AsyncClient):
        """Fetches a new captcha from RUNT API."""
        url = f"{RUNT_API_BASE}/captcha/libre-captcha/generar"
        try:
            response = await client.get(url, headers=HEADERS)
            response.raise_for_status()
            data = response.json()
            return data.get("id"), data.get("imagen")  # imagen is base64 string
        except Exception as e:
            logger.error(f"Error fetching RUNT captcha: {e}")
            raise HTTPException(status_code=502, detail="No se pudo obtener el captcha de RUNT")

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
            
            # Thresholding to remove noise (RUNT usually has white background with black/gray text)
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
            
            # 3. Solve with Tesseract
            # psm 7: Treat the image as a single text line.
            # -c tessedit_char_whitelist: Restrict to alphanumeric if known
            custom_config = r'--oem 3 --psm 7'
            captcha_text = pytesseract.image_to_string(thresh, config=custom_config)
            
            # Clean text
            captcha_text = "".join(filter(str.isalnum, captcha_text)).strip()
            
            logger.info(f"CAPTCHA solved (pytesseract): {captcha_text}")
            return captcha_text
        except Exception as e:
            logger.error(f"Error solving captcha: {e}")
            return ""

    @classmethod
    async def consultar_vehiculo(cls, placa: str, documento: str, client: httpx.AsyncClient = None) -> dict:
        """Main flow to consult vehicle information."""
        start_time = time.time()
        
        # Decide whether to use provided client or create a temporary one
        own_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
            own_client = True
            
        try:
            token = None
            general_info = {}
            max_attempts = 5
            
            for attempt in range(1, max_attempts + 1):
                logger.info(f"RUNT Auth Attempt {attempt}/{max_attempts}")
                
                # 1. Get and solve CAPTCHA
                id_captcha, img_base64 = await cls.get_captcha(client)
                
                # Run CPU-bound captcha solving in executor
                loop = asyncio.get_event_loop()
                solved_text = await loop.run_in_executor(None, cls.solve_captcha, img_base64)
                    
                if not solved_text or len(solved_text) != 5:
                    logger.warning(f"Attempt {attempt}: Bad captcha solve length, retrying...")
                    continue

                # 2. Authenticate
                auth_url = f"{RUNT_API_BASE}/auth"
                payload = {
                    "procedencia": "NACIONAL",
                    "tipoConsulta": "1",
                    "placa": placa.upper(),
                    "tipoDocumento": "C",
                    "documento": documento,
                    "vin": None,
                    "soat": None,
                    "aseguradora": "",
                    "rtm": None,
                    "reCaptcha": None,
                    "captcha": solved_text,
                    "valueCaptchaEncripted": "",
                    "idLibreCaptcha": id_captcha,
                    "verBannerSoat": True,
                    "configuracion": {"tiempoInactividad": "900", "tiempoCuentaRegresiva": "10"}
                }
                
                try:
                    auth_resp = await client.post(auth_url, json=payload, headers=HEADERS)
                    
                    if auth_resp.status_code == 200:
                        auth_data = auth_resp.json()
                        # 100% Parity: Keep all fields from RUNT auth
                        auth_veh_info = auth_data.get("infoVehiculo") or {}
                        general_info = auth_veh_info.copy()
                        
                        token = auth_resp.headers.get("Auth-Token") or auth_data.get("token")
                        if token:
                            logger.info(f"RUNT Auth Success on attempt {attempt}")
                            break # Success!
                    else:
                        logger.warning(f"Attempt {attempt} failed: {auth_resp.status_code} - {auth_resp.text}")
                except Exception as e:
                    logger.error(f"Error during Auth attempt {attempt}: {e}")
                
                # Wait a bit between retries
                if attempt < max_attempts:
                    await asyncio.sleep(0.5)

            if not token:
                raise HTTPException(status_code=401, detail="No se pudo autenticar con RUNT tras 5 intentos (Captcha incorrecto)")

            # 3. Fetch Detailed Data
            data_headers = HEADERS.copy()
            data_headers["Auth-Token"] = token if "Bearer" in token else f"Bearer {token}"
            
            # Fetch Technical Data
            tech_json = {}
            try:
                tech_url = f"{RUNT_API_BASE}/datos-tecnicos"
                tech_resp = await client.get(tech_url, headers=data_headers)
                if tech_resp.status_code == 200:
                    tech_json = tech_resp.json()
                    logger.debug(f"RAW Technical Data for {placa}: {str(tech_json)[:500]}...")
            except Exception as e:
                logger.warning(f"Could not fetch technical data for {placa}: {e}")

            # Robust extraction function
            def deep_get(data, keys, default=None):
                if not isinstance(data, dict): return default
                for key in keys:
                    # Try direct
                    if key in data and data[key]: return data[key]
                    # Try inside 'data', 'result', 'datosTecnicos'
                    for wrapper in ["data", "result", "datosTecnicos", "infoVehiculo"]:
                        inner = data.get(wrapper)
                        if isinstance(inner, dict) and inner.get(key):
                            return inner[key]
                return default

            # Update general_info ONLY IF missing or from tech_json provided a more complete value
            # This ensures we don't 'zero out' fields that we already have from infoVehiculo
            def add_missing(target, source, keys, target_key):
                val = deep_get(source, keys)
                if val and (not target.get(target_key) or target[target_key] == "null"):
                    target[target_key] = val

            add_missing(general_info, tech_json, ["numeroVin", "nroVin", "vin", "numeroChasis"], "vin")
            add_missing(general_info, tech_json, ["numeroMotor", "nroMotor", "motor"], "numMotor")
            add_missing(general_info, tech_json, ["fechaMatricula", "fechaMatriculaVehiculo", "fechaRegistro"], "fechaRegistro")
            add_missing(general_info, tech_json, ["cilindrada", "cilindraje"], "cilindraje")

            # Fetch SOAT Data
            soat_url = f"{RUNT_API_BASE}/soat"
            soat_resp = await client.get(soat_url, headers=data_headers)
            soat_raw = soat_resp.json() if soat_resp.status_code == 200 else []
            soat_data = []
            if isinstance(soat_raw, list):
                for s in soat_raw:
                    if isinstance(s, dict):
                        soat_data.append({
                            "estadoSoat": s.get("estado"),
                            "fechaVencimSoat": s.get("fechaVencimSoat")
                        })

            # Fetch RTM Data (Revisión Técnico-Mecánica)
            rtm_data = []
            for rtm_type in ["N", "0"]:
                try:
                    rtm_url = f"{RUNT_API_BASE}/rtms?tipo={rtm_type}"
                    rtm_resp = await client.get(rtm_url, headers=data_headers)
                    if rtm_resp.status_code == 200:
                        type_json = rtm_resp.json()
                        type_data = type_json.get("revisiones", []) if isinstance(type_json, dict) else []
                        
                        def parse_runt_date(date_str):
                            if not date_str: return datetime.min
                            date_str = str(date_str).strip()
                            try:
                                if "T" in date_str: return datetime.strptime(date_str[:10], "%Y-%m-%d")
                                return datetime.strptime(date_str, "%d/%m/%Y")
                            except:
                                try: return datetime.strptime(date_str, "%Y-%m-%d")
                                except: return datetime.min

                        if isinstance(type_data, list):
                            for item in type_data:
                                if isinstance(item, dict):
                                    # Search for results in common locations
                                    item_data = item.get("revision", item) if isinstance(item.get("revision"), dict) else item
                                    
                                    # 100% Parity: Calculate VIGENCIA
                                    # Use 'vigente' field if available (RUNT returns "SI")
                                    r_vigente = str(item_data.get("vigente", "")).strip().upper()
                                    r_estado = item_data.get("estado") or item_data.get("estadoRevision") or item_data.get("estadoRvt")
                                    r_vencimiento = item_data.get("fechaVencimiento") or item_data.get("fechaProximaRevision") or item_data.get("fechaVencimientoRvt")
                                    
                                    vigencia = "No vigente"
                                    if r_vigente == "SI":
                                        vigencia = "Vigente"
                                    elif r_estado and r_vencimiento:
                                        # Fallback to date calculation if 'vigente' is not "SI" or absent
                                        normal_state = str(r_estado).upper().strip()
                                        if normal_state in ["APROBADO", "APROBADA"]:
                                            v_date = parse_runt_date(r_vencimiento)
                                            if v_date >= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
                                                vigencia = "Vigente"

                                    rtm_data.append({
                                        "estadoRvt": r_estado,
                                        "vigencia": vigencia,
                                        "fechaVencimientoRvt": r_vencimiento,
                                        "kilometraje": item_data.get("kilometraje") or item_data.get("kmRevision") or item_data.get("kilometrajeRevision")
                                    })
                except Exception as e:
                    logger.warning(f"Error fetching RTM data for tipo={rtm_type}: {e}")
            
            # Combine all data sets
            combined_data = {
                "informacion_general": general_info,
                "datos_tecnicos": tech_json,
                "soat": soat_data,
                "revision_tecnico_mecanica": rtm_data
            }
            
            return {
                "exito": True,
                "data": combined_data,
                "tiempo_ejecucion": round(time.time() - start_time, 2)
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"RUNT API Error: {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail="Error en la comunicación con RUNT")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Internal Error in RUNT Service: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            if own_client:
                await client.aclose()
