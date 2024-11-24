"""
Logger configuration
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
from colorama import init, Fore, Style

# Initialize colorama for colored console output
init()

class ColoredFormatter(logging.Formatter):
    """Custom formatter for colored console output"""
    COLORS = {
        'DEBUG': Fore.BLUE,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        # Add color to the level name
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{Style.RESET_ALL}"
        return super().format(record)

def setup_logger(name: str = 'walkingpad') -> logging.Logger:
    """Configure and return a logger with enhanced formatting"""
    # Create logs directory if it doesn't exist
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - [%(levelname)s] - %(module)s:%(lineno)d - %(message)s'
    )

    # Colored console formatter
    console_formatter = ColoredFormatter(
        '%(asctime)s - [%(levelname)s] - %(message)s',
        datefmt='%H:%M:%S'
    )

    # File handler (rotating, max 10MB per file, keep 30 days of logs)
    today = datetime.now().strftime('%Y-%m-%d')
    file_handler = RotatingFileHandler(
        log_dir / f'walkingpad_{today}.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=30,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)

    # Console handler with colored output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)  # Changed to DEBUG to show all logs
    console_handler.setFormatter(console_formatter)

    # Remove existing handlers if any
    logger.handlers = []

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Create default logger
logger = setup_logger()

def get_logger() -> logging.Logger:
    """Get the configured logger"""
    return logger
