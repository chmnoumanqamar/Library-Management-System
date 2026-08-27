"""
Logging configuration for Library Management System.
Logs system events, transactions, security alerts, and errors.
"""

import logging
import os
import sys
from config import LOG_FILE

# Create logger
logger = logging.getLogger("LibraryManagementSystem")
logger.setLevel(logging.INFO)

# File handler
if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    
    # Formatter: ISO timestamp - Level - Message
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


def log_event(level: str, message: str) -> None:
    """Helper to log an event at the given log level."""
    lvl = level.upper()
    if lvl == "INFO":
        logger.info(message)
    elif lvl == "WARNING":
        logger.warning(message)
    elif lvl == "ERROR":
        logger.error(message)
    elif lvl == "CRITICAL":
        logger.critical(message)
    else:
        logger.debug(message)
