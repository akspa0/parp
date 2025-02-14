# adt_analyzer/__init__.py
"""ADT file analyzer package."""
from .parser import AdtFileParser
from .chunks import ChunkParsingError

__version__ = '0.1.0'

__all__ = [
    'AdtFileParser',
    'ChunkParsingError'
]