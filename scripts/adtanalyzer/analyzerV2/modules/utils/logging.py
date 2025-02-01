"""
Logging configuration for WoW Terrain Analyzer.
Provides consistent logging setup across the application.
"""
import logging
from pathlib import Path
from typing import Optional

def setup_logging(
    output_dir: Path,
    debug: bool = False,
    name: str = 'terrain_analyzer'
) -> logging.Logger:
    """
    Set up logging configuration
    
    Args:
        output_dir: Directory for log files
        debug: Enable debug logging
        name: Logger name
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create logs directory
    logs_dir = output_dir / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    # File handler
    log_path = logs_dir / f'{name}.log'
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(
        logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    )
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter('[%(levelname)s] %(message)s')
    )
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.addHandler(console_handler)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)

def log_exception(
    logger: logging.Logger,
    message: str,
    exc_info: Optional[Exception] = None
) -> None:
    """
    Log an exception with consistent formatting
    
    Args:
        logger: Logger instance
        message: Error message
        exc_info: Optional exception info
    """
    if exc_info:
        logger.error(f"{message}: {exc_info}", exc_info=True)
    else:
        logger.error(message)