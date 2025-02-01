"""
Utility modules for ADT analysis.
"""
from .binary import (
    read_packed_string,
    read_string_block,
    normalize_model_path,
    pack_vector3,
    unpack_vector3,
    pack_quaternion,
    unpack_quaternion,
    read_chunks,
    detect_chunk_reversal,
    decompress_alpha_map
)
from .logging import LogManager, LoggerAdapter, get_logger
from .common_types import (
    Vector2D,
    Vector3D,
    Quaternion,
    CAaBox,
    RGB,
    RGBA,
    read_cstring,
    read_fixed_point,
    read_packed_bits,
    pack_bits,
    pack_cstring
)

__all__ = [
    # Binary utilities
    'read_packed_string',
    'read_string_block',
    'normalize_model_path',
    'pack_vector3',
    'unpack_vector3',
    'pack_quaternion',
    'unpack_quaternion',
    'read_chunks',
    'detect_chunk_reversal',
    'decompress_alpha_map',
    
    # Logging utilities
    'LogManager',
    'LoggerAdapter',
    'get_logger',
    
    # Common types
    'Vector2D',
    'Vector3D',
    'Quaternion',
    'CAaBox',
    'RGB',
    'RGBA',
    'read_cstring',
    'read_fixed_point',
    'read_packed_bits',
    'pack_bits',
    'pack_cstring'
]