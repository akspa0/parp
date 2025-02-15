"""Logging configuration for ADT analyzer."""
import logging
import sys
from pathlib import Path
from datetime import datetime

def setup_logging(log_dir: str, log_level: int = logging.INFO) -> None:
    """Setup logging configuration.
    
    Args:
        log_dir: Directory to store log files
        log_level: Logging level (default: INFO)
        
    Creates two handlers:
    1. File handler that writes to a timestamped file in log_dir
    2. Console handler that writes to stderr
    """
    # Create log directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Create file handler
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_path / f'adt_analyzer_{timestamp}.log'
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(log_level)
    root_logger.addHandler(file_handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # Log initial message
    root_logger.info(f"Logging initialized at {log_level}")
    root_logger.info(f"Log file: {log_file}")