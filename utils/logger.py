import logging
import os
from datetime import datetime

# Ensure logs directory exists
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    try:
        os.makedirs(LOG_DIR)
    except: pass

# Setup File Handler
log_file = os.path.join(LOG_DIR, "app.log")

# Create a custom logger
logger = logging.getLogger("app_logger")
logger.setLevel(logging.DEBUG)

# Check if handler already exists to avoid duplicate logs on reload
if not logger.handlers:
    try:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(module)s: %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to setup logger: {e}")

def log_debug(msg):
    logger.debug(msg)

def log_info(msg):
    logger.info(msg)

def log_error(msg):
    logger.error(msg)

def log_warning(msg):
    logger.warning(msg)
