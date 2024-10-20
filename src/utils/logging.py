import logging
from logging.handlers import RotatingFileHandler
import sys
from typing import Dict, Any
from config import LOG_LEVEL, LOG_FILE

RESET = "\033[0m"
def print_pink(text):
    # ANSI escape code for pink is 95 (bright magenta)
    PINK = "\033[95m"
    print(f"{PINK}{text}{RESET}")

def print_red(text):
    # ANSI escape code for red is 91 (bright red)
    RED = "\033[91m"
    print(f"{RED}{text}{RESET}")

def print_green(text):
    # ANSI escape code for green is 92 (bright green)
    GREEN = "\033[92m"
    print(f"{GREEN}{text}{RESET}")

def print_blue(text):
    # ANSI escape code for blue is 94 (bright blue)
    BLUE = "\033[94m"
    print(f"{BLUE}{text}{RESET}")

def log_tool_use(tool_name, input_params, output):
    # using blue color for tool logs
    print_blue(f"Tool used: {tool_name}")
    print_blue(f"Input: {input_params}")
    print_blue(f"Output: {output}")

def wrapped_tool(func):
    """
    Log stuff when the tools have completed execution.
    """
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        log_tool_use(func.__name__, args, result)
        return result
    return wrapper


def setup_logger():
    """
    Set up and configure the logger for the application.
    """
    logger = logging.getLogger("concierge_workflow")
    logger.setLevel(LOG_LEVEL)

    # Create handlers
    c_handler = logging.StreamHandler(sys.stdout)
    f_handler = RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5)

    # Create formatters and add it to handlers
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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
