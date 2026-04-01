import logging
import os
from logging.handlers import TimedRotatingFileHandler

LOG_DIR = "logs"
LOG_FILE = "app.log"

# Create logs directory
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, LOG_FILE)

# Ensure logs directory exists
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("fastapi_app")

if not logger.handlers:
  logger.setLevel(logging.INFO)
  formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
  )

  console_handler = logging.StreamHandler()
  console_handler.setFormatter(formatter)

  file_handler = logging.FileHandler(LOG_PATH)
  file_handler.setFormatter(formatter)

  file_handler = TimedRotatingFileHandler(
    LOG_PATH, 
    when="midnight", 
    interval=1, 
    backupCount=30,
    encoding="utf-8"
  )
  file_handler.suffix = "%Y-%m-%d" 
  file_handler.setFormatter(formatter)

  logger.addHandler(console_handler)
  logger.addHandler(file_handler)