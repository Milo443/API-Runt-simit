# ---------------------------------------------------------
# Autor: Camilo Calderon
# Github: @Milo443
# Nota: Desarrollado con amor por Milo
# Mensaje: usa el vibecoding y los agentes responsablemente.
# ---------------------------------------------------------
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "Orquestador RUNT API"
    VERSION: str = "1.0.0"
    APP_ENV: str = "dev"
    DB_THREAD_WORKERS: int = 5
    
    # OCR config
    TESSERACT_CMD: str = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    OMP_THREAD_LIMIT: int = 1
    
    # Mass Processing
    BATCH_SIZE: int = 10
    
    # RUNT API URLs
    RUNT_VEHICULO_API_BASE: str = "https://runtproapi.runt.gov.co/CYRConsultaVehiculoMS"
    RUNT_CIUDADANO_API_BASE: str = "https://runtproapi.runt.gov.co/CYRConsultaCiudadanoMS"
    
    # SIMIT API URLs
    SIMIT_API_BASE: str = "https://consultasimit.fcm.org.co/simit/microservices/estado-cuenta-simit"
    SIMIT_CAPTCHA_API: str = "https://qxcaptcha.fcm.org.co/api.php"
    
    # Logging
    LOG_DIR: str = "logs"
    LOG_LEVEL: str = "INFO"
    LOG_RETENTION_DAYS: int = 4
    
    # JWT & Auth
    JWT_SECRET_KEY: str = "GaneRedcolsaApi-2024*"
    JWT_ALGORITHM: str = "HS512"
    SCREEN_ID_INDIVIDUAL: str = "71"
    SCREEN_ID_MASIVA: str = "74"
    
    # Storage settings
    STORAGE_DIR: str = "storage"
    STORAGE_MASS_RESULTS: str = "storage/mass_results"
    
    # Database Pool Settings (commented out)
    # DB_POOL_SIZE: int = 1
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
