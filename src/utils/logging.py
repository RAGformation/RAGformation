import logging
from logging.handlers import RotatingFileHandler
import sys
from typing import Dict, Any
from config import LOG_LEVEL, LOG_FILE

def setup_logger():
    """
    Set up and configure the logger for the application.
    """
    logger = logging.getLogger('concierge_workflow')
    logger.setLevel(LOG_LEVEL)

    # Create handlers
    c_handler = logging.StreamHandler(sys.stdout)
    f_handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5)

    # Create formatters and add it to handlers
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    c_format = logging.Formatter(log_format)
    f_format = logging.Formatter(log_format)
    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)

    # Add handlers to the logger
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

    return logger

logger = setup_logger()

def log_error(message: str):
    """
    Log an error message.

    Args:
    message (str): The error message to log.
    """
    logger.error(message)

def log_warning(message: str):
    """
    Log a warning message.

    Args:
    message (str): The warning message to log.
    """
    logger.warning(message)

def log_info(message: str):
    """
    Log an info message.

    Args:
    message (str): The info message to log.
    """
    logger.info(message)

def log_debug(message: str):
    """
    Log a debug message.

    Args:
    message (str): The debug message to log.
    """
    logger.debug(message)