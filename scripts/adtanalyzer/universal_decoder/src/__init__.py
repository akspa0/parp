"""
Universal WoW Map File Decoder
Core components and utilities
"""

from .format_detector import FormatDetector, FileFormat, FileType
from .chunks import (
    ChunkRegistry, ChunkFormat, chunk_registry,
    ChunkDecoder, Vector3D
)
from .output import JSONOutputHandler

__version__ = '1.0.0'

__all__ = [
    # Format detection
    'FormatDetector',
    'FileFormat',
    'FileType',
    
    # Chunk handling
    'ChunkRegistry',
    'ChunkFormat',
    'chunk_registry',
    'ChunkDecoder',
    'Vector3D',
    
    # Output handling
    'JSONOutputHandler',
    
    # Version
    '__version__'
]