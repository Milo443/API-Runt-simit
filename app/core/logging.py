import logging
import sys
import os
from logging.handlers import TimedRotatingFileHandler
from .config import settings

def setup_logging():
    # 1. Ensure logs directory exists
    log_dir = settings.LOG_DIR
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, "app.log")
    
    # 2. Define Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 3. Handlers
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Daily Rotating File Handler
    file_handler = TimedRotatingFileHandler(
        log_file,
        when="D",       # Rotate every day
        interval=1,     # 1 day
        backupCount=settings.LOG_RETENTION_DAYS,  # Keep 4 days
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.suffix = "%Y-%m-%d"  # Append date to filename on rotation

    # 4. Global Config
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)
    
    # Remove existing handlers to avoid duplicates on reload
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    logger = logging.getLogger("app")
    logger.info(f"Logging system initialized. Current log file: {log_file}")
    
# Initialize on import
setup_logging()
logger = logging.getLogger("app")
