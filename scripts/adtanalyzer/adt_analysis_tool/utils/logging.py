"""
Logging configuration for ADT analysis tool.
Provides consistent logging setup and formatters.
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

class LogManager:
    """Manages logging configuration and setup"""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize logging manager
        
        Args:
            base_dir: Base directory for log files. If None, uses current directory.
        """
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create logs directory if it doesn't exist
        self.log_dir = self.base_dir / 'logs'
        self.log_dir.mkdir(exist_ok=True)
        
        # Initialize loggers
        self.main_logger = logging.getLogger('adt_analyzer')
        self.parser_logger = logging.getLogger('adt_parser')
        self.missing_logger = logging.getLogger('missing_files')
        
        self._configure_logging()
        
    def _configure_logging(self):
        """Configure logging formatters and handlers"""
        # Clear any existing handlers
        for logger in [self.main_logger, self.parser_logger, self.missing_logger]:
            logger.handlers.clear()
            
        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_formatter = logging.Formatter(
            '[%(levelname)s] %(message)s'
        )
        
        # Configure main logger
        self.main_logger.setLevel(logging.INFO)
        
        main_file_handler = logging.FileHandler(
            self.log_dir / f'adt_analyzer_{self.timestamp}.log',
            encoding='utf-8'
        )
        main_file_handler.setFormatter(file_formatter)
        main_file_handler.setLevel(logging.DEBUG)
        
        main_console_handler = logging.StreamHandler(sys.stdout)
        main_console_handler.setFormatter(console_formatter)
        main_console_handler.setLevel(logging.INFO)
        
        self.main_logger.addHandler(main_file_handler)
        self.main_logger.addHandler(main_console_handler)
        
        # Configure parser logger
        self.parser_logger.setLevel(logging.DEBUG)
        
        parser_file_handler = logging.FileHandler(
            self.log_dir / f'parser_{self.timestamp}.log',
            encoding='utf-8'
        )
        parser_file_handler.setFormatter(file_formatter)
        parser_file_handler.setLevel(logging.DEBUG)
        
        self.parser_logger.addHandler(parser_file_handler)
        
        # Configure missing files logger
        self.missing_logger.setLevel(logging.INFO)
        
        missing_file_handler = logging.FileHandler(
            self.log_dir / f'missing_files_{self.timestamp}.log',
            encoding='utf-8'
        )
        missing_file_handler.setFormatter(file_formatter)
        
        self.missing_logger.addHandler(missing_file_handler)
        
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger by name
        
        Args:
            name: Logger name
            
        Returns:
            Configured logger instance
        """
        if name == 'main':
            return self.main_logger
        elif name == 'parser':
            return self.parser_logger
        elif name == 'missing':
            return self.missing_logger
        else:
            # Create child logger of main
            logger = self.main_logger.getChild(name)
            logger.setLevel(logging.DEBUG)
            return logger
            
    def log_error(self, message: str, exc_info: Optional[Exception] = None):
        """
        Log an error message
        
        Args:
            message: Error message
            exc_info: Optional exception info to include
        """
        if exc_info:
            self.main_logger.error(message, exc_info=exc_info)
        else:
            self.main_logger.error(message)
            
    def log_missing_file(self, filename: str, referenced_by: str):
        """
        Log a missing file reference
        
        Args:
            filename: Name of missing file
            referenced_by: Name of file that referenced it
        """
        self.missing_logger.info(f"Missing file: {filename} referenced by {referenced_by}")
        
    def log_stats(self, stats: dict):
        """
        Log processing statistics
        
        Args:
            stats: Dictionary of statistics to log
        """
        self.main_logger.info("Processing Statistics:")
        for key, value in stats.items():
            self.main_logger.info(f"  {key}: {value}")
            
class LoggerAdapter(logging.LoggerAdapter):
    """Adds context information to log messages"""
    
    def process(self, msg, kwargs):
        """Add context to message if available"""
        if self.extra:
            context_str = ' '.join(f'{k}={v}' for k, v in self.extra.items())
            msg = f'{msg} [{context_str}]'
        return msg, kwargs

def get_logger(name: str, **context) -> Union[logging.Logger, LoggerAdapter]:
    """
    Get a logger with optional context
    
    Args:
        name: Logger name
        **context: Optional context key-value pairs
        
    Returns:
        Logger or LoggerAdapter instance
    """
    logger = logging.getLogger(name)
    if context:
        return LoggerAdapter(logger, context)
    return logger