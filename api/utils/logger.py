"""
Logger configuration
"""
import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logger(name: str = 'walkingpad') -> logging.Logger:
    """Configure and return a logger"""
    # Create logs directory if it doesn't exist
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )

    # File handler (daily rotating)
    today = datetime.now().strftime('%Y-%m-%d')
    file_handler = logging.FileHandler(
        log_dir / f'walkingpad_{today}.log',
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Create default logger
logger = setup_logger()


def get_logger() -> logging.Logger:
    """Get the configured logger"""
    return logger
