"""
Utility functions for WoW Terrain Analyzer.
Provides common functionality used across the application.
"""

from .logging import setup_logging, get_logger, log_exception

__all__ = [
    'setup_logging',
    'get_logger',
    'log_exception',
]

# Constants
CHUNK_SIZE = 1024 * 1024  # 1MB for file reading
MAX_RETRIES = 3           # Default retry count for operations
TIMEOUT = 30              # Default timeout in seconds

# Common type aliases
from typing import Dict, List, Optional, Set, Tuple, Union
from pathlib import Path

PathLike = Union[str, Path]
JsonDict = Dict[str, any]
Coordinates = Tuple[int, int]

__all__ += [
    'CHUNK_SIZE',
    'MAX_RETRIES',
    'TIMEOUT',
    'PathLike',
    'JsonDict',
    'Coordinates',
]