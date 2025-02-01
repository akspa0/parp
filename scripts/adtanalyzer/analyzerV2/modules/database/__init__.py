"""
Database functionality for WoW Terrain Analyzer.
Provides schema definition and database operations.
"""

from .schema import init_database, SCHEMA_VERSION
from .ops import DatabaseManager, compress_array

__all__ = [
    'init_database',
    'SCHEMA_VERSION',
    'DatabaseManager',
    'compress_array',
]

# Type aliases
from typing import Dict, List, Optional, Set, Tuple, Union
from pathlib import Path

DBRecord = Dict[str, any]
DBConnection = 'sqlite3.Connection'
DBCursor = 'sqlite3.Cursor'

__all__ += [
    'DBRecord',
    'DBConnection',
    'DBCursor',
]

# Constants
DEFAULT_BATCH_SIZE = 1000
MAX_CONNECTIONS = 8
SQLITE_MAX_VARIABLES = 999  # SQLite limit on variables per statement

__all__ += [
    'DEFAULT_BATCH_SIZE',
    'MAX_CONNECTIONS',
    'SQLITE_MAX_VARIABLES',
]