"""
JSON handling for WoW terrain data.
Provides encoding and decoding of terrain data structures.
"""

from .encoder import (
    TerrainEncoder,
    encode_terrain_file,
    save_terrain_file,
)

from .decoder import (
    load_terrain_file,
    decode_adt_file,
    decode_wdt_file,
)

class JSONHandler:
    """High-level interface for JSON operations"""
    
    @staticmethod
    def save(terrain_file, output_path):
        """Save terrain file to JSON"""
        return save_terrain_file(terrain_file, output_path)
    
    @staticmethod
    def load(json_path):
        """Load terrain file from JSON"""
        return load_terrain_file(json_path)
    
    @staticmethod
    def encode(terrain_file):
        """Encode terrain file to JSON string"""
        return encode_terrain_file(terrain_file)

__all__ = [
    # Main interface
    'JSONHandler',
    
    # Encoder
    'TerrainEncoder',
    'encode_terrain_file',
    'save_terrain_file',
    
    # Decoder
    'load_terrain_file',
    'decode_adt_file',
    'decode_wdt_file',
]

# Type aliases
from typing import Dict, List, Optional, Set, Tuple, Union
from pathlib import Path

JsonDict = Dict[str, any]
JsonList = List[JsonDict]
JsonPath = Union[str, Path]

__all__ += [
    'JsonDict',
    'JsonList',
    'JsonPath',
]