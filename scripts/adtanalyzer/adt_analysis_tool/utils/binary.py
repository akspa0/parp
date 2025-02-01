"""
Binary data handling utilities for ADT parsing.
"""
import struct
from typing import List, Optional, Tuple, Union

def read_packed_string(data: bytes, offset: int = 0) -> Tuple[str, int]:
    """
    Read null-terminated string from binary data
    
    Args:
        data: Binary data to read from
        offset: Starting offset in data
        
    Returns:
        Tuple of (string, new offset)
    """
    end = data.find(b'\0', offset)
    if end == -1:
        return data[offset:].decode('utf-8', errors='replace'), len(data)
    return data[offset:end].decode('utf-8', errors='replace'), end + 1

def read_string_block(data: bytes) -> List[str]:
    """
    Parse block of null-terminated strings
    
    Args:
        data: Binary data containing strings
        
    Returns:
        List of strings
    """
    strings = []
    offset = 0
    while offset < len(data):
        string, new_offset = read_packed_string(data, offset)
        if string:
            strings.append(string)
        if new_offset <= offset:
            break
        offset = new_offset
    return strings

def normalize_model_path(path: str) -> str:
    """
    Normalize model file path
    
    Args:
        path: Original file path
        
    Returns:
        Normalized path
    """
    # Convert to lowercase and normalize slashes
    path = path.lower().replace('\\', '/')
    
    # Remove leading ./ or /
    path = path.lstrip('./').lstrip('/')
    
    # Convert .mdx to .m2
    if path.endswith('.mdx'):
        path = path[:-4] + '.m2'
        
    return path

def pack_vector3(x: float, y: float, z: float) -> bytes:
    """Pack 3D vector to bytes"""
    return struct.pack('<3f', x, y, z)

def unpack_vector3(data: bytes, offset: int = 0) -> Tuple[float, float, float]:
    """Unpack 3D vector from bytes"""
    return struct.unpack('<3f', data[offset:offset+12])

def pack_quaternion(x: float, y: float, z: float, w: float) -> bytes:
    """Pack quaternion to bytes"""
    return struct.pack('<4f', x, y, z, w)

def unpack_quaternion(data: bytes, offset: int = 0) -> Tuple[float, float, float, float]:
    """Unpack quaternion from bytes"""
    return struct.unpack('<4f', data[offset:offset+16])

def read_chunks(data: bytes, reversed_names: bool = False) -> List[Tuple[bytes, bytes]]:
    """
    Read all chunks from binary data
    
    Args:
        data: Binary data to parse
        reversed_names: Whether chunk names are reversed
        
    Returns:
        List of (chunk_name, chunk_data) tuples
    """
    chunks = []
    offset = 0
    while offset + 8 <= len(data):
        # Read chunk header
        chunk_name = data[offset:offset+4]
        if reversed_names:
            chunk_name = chunk_name[::-1]
        chunk_size = struct.unpack('<I', data[offset+4:offset+8])[0]
        
        # Validate chunk size
        if offset + 8 + chunk_size > len(data):
            break
            
        # Extract chunk data
        chunk_data = data[offset+8:offset+8+chunk_size]
        chunks.append((chunk_name, chunk_data))
        
        offset += 8 + chunk_size
        
    return chunks

def detect_chunk_reversal(data: bytes) -> bool:
    """
    Detect if chunk names are reversed
    
    Args:
        data: Start of file data
        
    Returns:
        True if chunk names appear to be reversed
    """
    # Try parsing first few chunks both ways
    normal_chunks = read_chunks(data[:1024], reversed_names=False)
    reversed_chunks = read_chunks(data[:1024], reversed_names=True)
    
    # Look for known chunk names
    known_chunks = {b'MVER', b'MHDR', b'MCIN', b'MTEX'}
    
    normal_known = any(name in known_chunks for name, _ in normal_chunks)
    reversed_known = any(name in known_chunks for name, _ in reversed_chunks)
    
    if normal_known and not reversed_known:
        return False
    if reversed_known and not normal_known:
        return True
        
    # Default to normal if can't determine
    return False

def decompress_alpha_map(data: bytes, width: int = 64, height: int = 64) -> bytes:
    """
    Decompress MCAL alpha map data
    
    Args:
        data: Compressed alpha map data
        width: Alpha map width
        height: Alpha map height
        
    Returns:
        Decompressed alpha map data
    """
    if not data:
        return b'\0' * (width * height)
        
    result = bytearray(width * height)
    pos = 0
    offset = 0
    
    while offset < len(data):
        # Read control byte
        control = data[offset]
        offset += 1
        
        if control & 0x80:
            # Fill mode
            count = (control & 0x7F) + 1
            if offset >= len(data):
                break
            value = data[offset]
            offset += 1
            
            for i in range(count):
                if pos >= len(result):
                    break
                result[pos] = value
                pos += 1
        else:
            # Copy mode
            count = control + 1
            if offset + count > len(data):
                break
            
            for i in range(count):
                if pos >= len(result):
                    break
                result[pos] = data[offset + i]
                pos += 1
                
            offset += count
            
    return bytes(result)