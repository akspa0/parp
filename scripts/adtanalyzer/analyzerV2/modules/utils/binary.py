"""
Binary data utilities for WoW terrain files.
Provides functions for reading and manipulating binary data.
"""
import struct
from typing import List, Tuple, Union

def read_packed_float(data: bytes, offset: int = 0) -> Tuple[float, int]:
    """
    Read a packed float value
    
    Args:
        data: Binary data
        offset: Starting offset
        
    Returns:
        Tuple of (float_value, bytes_read)
    """
    value = struct.unpack_from('<f', data, offset)[0]
    return value, 4

def read_packed_int(data: bytes, offset: int = 0) -> Tuple[int, int]:
    """
    Read a packed integer value
    
    Args:
        data: Binary data
        offset: Starting offset
        
    Returns:
        Tuple of (int_value, bytes_read)
    """
    value = struct.unpack_from('<i', data, offset)[0]
    return value, 4

def read_packed_uint(data: bytes, offset: int = 0) -> Tuple[int, int]:
    """
    Read a packed unsigned integer value
    
    Args:
        data: Binary data
        offset: Starting offset
        
    Returns:
        Tuple of (uint_value, bytes_read)
    """
    value = struct.unpack_from('<I', data, offset)[0]
    return value, 4

def read_packed_short(data: bytes, offset: int = 0) -> Tuple[int, int]:
    """
    Read a packed short value
    
    Args:
        data: Binary data
        offset: Starting offset
        
    Returns:
        Tuple of (short_value, bytes_read)
    """
    value = struct.unpack_from('<h', data, offset)[0]
    return value, 2

def read_packed_ushort(data: bytes, offset: int = 0) -> Tuple[int, int]:
    """
    Read a packed unsigned short value
    
    Args:
        data: Binary data
        offset: Starting offset
        
    Returns:
        Tuple of (ushort_value, bytes_read)
    """
    value = struct.unpack_from('<H', data, offset)[0]
    return value, 2

def read_packed_byte(data: bytes, offset: int = 0) -> Tuple[int, int]:
    """
    Read a packed byte value
    
    Args:
        data: Binary data
        offset: Starting offset
        
    Returns:
        Tuple of (byte_value, bytes_read)
    """
    value = data[offset]
    return value, 1

def read_packed_string(data: bytes, offset: int = 0, length: int = None) -> Tuple[str, int]:
    """
    Read a packed string value
    
    Args:
        data: Binary data
        offset: Starting offset
        length: String length (None for null-terminated)
        
    Returns:
        Tuple of (string_value, bytes_read)
    """
    if length is None:
        # Find null terminator
        end = offset
        while end < len(data) and data[end] != 0:
            end += 1
        length = end - offset
        
    value = data[offset:offset + length].decode('utf-8').rstrip('\0')
    return value, length

def read_packed_vec3(data: bytes, offset: int = 0) -> Tuple[List[float], int]:
    """
    Read a packed 3D vector
    
    Args:
        data: Binary data
        offset: Starting offset
        
    Returns:
        Tuple of ([x, y, z], bytes_read)
    """
    values = struct.unpack_from('<3f', data, offset)
    return list(values), 12

def read_packed_vec2(data: bytes, offset: int = 0) -> Tuple[List[float], int]:
    """
    Read a packed 2D vector
    
    Args:
        data: Binary data
        offset: Starting offset
        
    Returns:
        Tuple of ([x, y], bytes_read)
    """
    values = struct.unpack_from('<2f', data, offset)
    return list(values), 8

def read_packed_rgba(data: bytes, offset: int = 0) -> Tuple[List[int], int]:
    """
    Read a packed RGBA color value
    
    Args:
        data: Binary data
        offset: Starting offset
        
    Returns:
        Tuple of ([r, g, b, a], bytes_read)
    """
    values = struct.unpack_from('<4B', data, offset)
    return list(values), 4

def pack_float(value: float) -> bytes:
    """Pack float value to bytes"""
    return struct.pack('<f', value)

def pack_int(value: int) -> bytes:
    """Pack integer value to bytes"""
    return struct.pack('<i', value)

def pack_uint(value: int) -> bytes:
    """Pack unsigned integer value to bytes"""
    return struct.pack('<I', value)

def pack_short(value: int) -> bytes:
    """Pack short value to bytes"""
    return struct.pack('<h', value)

def pack_ushort(value: int) -> bytes:
    """Pack unsigned short value to bytes"""
    return struct.pack('<H', value)

def pack_byte(value: int) -> bytes:
    """Pack byte value to bytes"""
    return bytes([value])

def pack_string(value: str, length: int = None) -> bytes:
    """Pack string value to bytes"""
    encoded = value.encode('utf-8')
    if length is not None:
        encoded = encoded.ljust(length, b'\0')
    return encoded + b'\0'

def pack_vec3(values: List[float]) -> bytes:
    """Pack 3D vector to bytes"""
    return struct.pack('<3f', *values)

def pack_vec2(values: List[float]) -> bytes:
    """Pack 2D vector to bytes"""
    return struct.pack('<2f', *values)

def pack_rgba(values: List[int]) -> bytes:
    """Pack RGBA color value to bytes"""
    return struct.pack('<4B', *values)