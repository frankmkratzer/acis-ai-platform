"""
Centralized logging configuration
"""

import os
import sys

from loguru import logger

# Get log level from environment
LOG_LEVEL = os.getenv("AI_LOG_LEVEL", "INFO")

# Remove default handler
logger.remove()

# Add console handler with custom format
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=LOG_LEVEL,
    colorize=True,
)

# Optionally add file handler
if os.getenv("AI_LOG_TO_FILE", "0") == "1":
    log_file = os.getenv("AI_LOG_FILE", "acis_ai_platform.log")
    logger.add(
        log_file,
        rotation="10 MB",
        retention="7 days",
        level=LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )


def get_logger(name: str):
    """Get a logger instance with module name"""
    return logger.bind(name=name)
