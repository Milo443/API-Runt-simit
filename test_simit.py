from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import json, time, threading

# ═══════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════
SIMIT_URL    = "https://www.fcm.org.co/simit/#/estado-cuenta"
CONSULTA_URL = "https://consultasimit.fcm.org.co/simit/microservices/estado-cuenta-simit/estadocuenta/consulta"
REFILL_TARGET   = 4   # tokens a acumular en cada recarga
REFILL_THRESHOLD = 2  # disparar recarga cuando quedan <= N tokens

BLOCKED_URLS = [
    "*google-analytics.com/*", "*analytics.google.com/*",
    "*googleads*", "*doubleclick.net/*", "*facebook.com/tr*",
    "*googleadservices.com/*", "*googletagmanager.com/*",
    "*civii.co/*", "*paymentez.com/*",
    "*.png", "*.jpg", "*.jpeg", "*.gif", "*.svg", "*.ico",
    "*.woff", "*.woff2", "*.ttf",
]

# ═══════════════════════════════════════════════════════════════════════
# DRIVER SINGLETON
# ═══════════════════════════════════════════════════════════════════════
_driver  = None
_warming = False
_initialized = False  # saber si ya navegó al sitio al menos una vez

def get_driver() -> webdriver.Chrome:
    global _driver
    if _driver is None:
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--blink-settings=imagesEnabled=false")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        _driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )
        _driver.execute_cdp_cmd("Network.enable", {})
        _driver.execute_cdp_cmd("Network.setBlockedURLs", {"urls": BLOCKED_URLS})
    return _driver


# ═══════════════════════════════════════════════════════════════════════
# TOKEN POOL
# ═══════════════════════════════════════════════════════════════════════
def _token_count() -> int:
    try:
        raw = get_driver().execute_script("return sessionStorage.getItem('whcQuestions');")
        if not raw:
            return 0
        return len(json.loads(raw).get("questions", []))
    except:
        return 0


def _refill_tokens():
    """Navega/recarga para generar tokens frescos. Siempre corre en background."""
    global _warming, _initialized
    if _warming:
        return
    _warming = True
    try:
        driver = get_driver()
        if _initialized:
            # Ya estaba en el sitio — limpiar y recargar
            driver.execute_script("sessionStorage.clear();")
            driver.execute_script("location.reload();")
        else:
            # Primera vez — navegar
            driver.get(SIMIT_URL)
            _initialized = True

        # Esperar hasta REFILL_TARGET tokens
        for _ in range(80):
            time.sleep(0.5)
            if _token_count() >= REFILL_TARGET:
                break

        print(f"  [pool] {_token_count()} tokens listos")
    finally:
        _warming = False


def _wait_for_token(timeout: int = 35) -> bool:
    for _ in range(timeout * 2):
        if _token_count() > 0:
            return True
        time.sleep(0.5)
    return False


# ═══════════════════════════════════════════════════════════════════════
# API PÚBLICA
# ═══════════════════════════════════════════════════════════════════════
def warmup():
    """Llamar una vez al iniciar la aplicación."""
    print(">> Calentando token pool...")
    t0 = time.time()
    _refill_tokens()  # síncrono en el startup
    print(f"  Listo en {time.time()-t0:.2f}s — {_token_count()} tokens\n")


def consultar_simit(filtro: str) -> dict:
    """
    Consulta el estado de cuenta SIMIT para una cédula o placa.
    Raises: TimeoutError, Exception
    """
    t0     = time.time()
    driver = get_driver()

    # Sin tokens → esperar refill
    if _token_count() == 0:
        if not _warming:
            threading.Thread(target=_refill_tokens, daemon=True).start()
        if not _wait_for_token():
            raise TimeoutError("Captcha no resolvió en 35s")

    print(f"  Tokens disponibles: {_token_count()} | espera: {time.time()-t0:.2f}s")

    # Fetch desde el browser — usa sus cookies y TLS nativos
    result = driver.execute_script("""
        return new Promise(async (resolve) => {
            try {
                var data      = JSON.parse(sessionStorage.getItem('whcQuestions'));
                var questions = data.questions;
                var last      = questions.pop();
                sessionStorage.setItem('whcQuestions', JSON.stringify({questions: questions}));

                var tokenArray = Array.isArray(last) ? last : [last];

                var resp = await fetch(arguments[1], {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'Accept': '*/*'},
                    body: JSON.stringify({
                        filtro: arguments[0],
                        reCaptchaDTO: {
                            response: JSON.stringify(tokenArray),
                            consumidor: "1"
                        }
                    })
                });
                resolve({status: resp.status, body: await resp.text()});
            } catch(e) {
                resolve({error: e.toString()});
            }
        });
    """, filtro, CONSULTA_URL)

    elapsed   = time.time() - t0
    remaining = _token_count()
    print(f"  Total: {elapsed:.2f}s | tokens restantes: {remaining}")

    # Refill anticipado
    if remaining <= REFILL_THRESHOLD and not _warming:
        threading.Thread(target=_refill_tokens, daemon=True).start()
        print("  Recarga en background iniciada")

    if "error" in result:
        raise Exception(result["error"])
    if result["status"] != 200:
        raise Exception(f"HTTP {result['status']}: {result['body']}")

    return json.loads(result["body"])


# ═══════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    warmup()

    cedulas = ["1193170379"] * 7
    for i, cedula in enumerate(cedulas):
        print(f">> Consulta {i+1}: {cedula}")
        t = time.time()
        try:
            data = consultar_simit(cedula)
            print(f"  paz_y_salvo: {data['pazSalvo']} | total: ${data['totalGeneral']:,} | tiempo: {time.time()-t:.2f}s\n")
        except Exception as e:
            print(f"  ERROR: {e}\n")