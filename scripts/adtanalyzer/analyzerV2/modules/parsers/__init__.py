"""
File parsers for WoW terrain data.
Provides parsers for ADT and WDT files.
"""

from .base import (
    ParserError,
    ChunkError,
    BaseParser,
)

# Import parsers
from .adt import ADTParser
from .wdt import WDTParser

__all__ = [
    # Base classes
    'ParserError',
    'ChunkError',
    'BaseParser',
    
    # Parsers
    'ADTParser',
    'WDTParser',
]

# Type aliases
from typing import Dict, List, Optional, Set, Tuple, Union
from pathlib import Path

ChunkData = Dict[str, any]
ChunkMap = Dict[Tuple[int, int], ChunkData]
FileOffset = int
ChunkSize = int
ChunkHeader = Tuple[str, ChunkSize]
ChunkInfo = Tuple[FileOffset, ChunkSize]

__all__ += [
    'ChunkData',
    'ChunkMap',
    'FileOffset',
    'ChunkSize',
    'ChunkHeader',
    'ChunkInfo',
]

# Constants
CHUNK_MAGIC = {
    'MVER': 'Version',
    'MHDR': 'Header',
    'MCIN': 'ChunkInfo',
    'MTEX': 'Textures',
    'MMDX': 'Models',
    'MMID': 'ModelIds',
    'MWMO': 'WMOs',
    'MWID': 'WMOIds',
    'MDDF': 'DoodadDefs',
    'MODF': 'WMODefs',
    'MCNK': 'MapChunk',
    'MFBO': 'FogBands',
    'MTFX': 'TerrainFx',
    'MTXF': 'TextureFlags',
}

__all__ += [
    'CHUNK_MAGIC',
]