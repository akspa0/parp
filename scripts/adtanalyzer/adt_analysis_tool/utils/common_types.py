"""
Common data types used in WoW file formats.
Based on: https://wowdev.wiki/Common_Types
"""
import struct
from typing import List, Tuple, Union, Optional
from dataclasses import dataclass
import math

@dataclass
class Vector2D:
    """2D vector"""
    x: float
    y: float
    
    @classmethod
    def unpack(cls, data: bytes, offset: int = 0) -> 'Vector2D':
        """Unpack from binary data"""
        x, y = struct.unpack('<2f', data[offset:offset+8])
        return cls(x, y)
        
    def pack(self) -> bytes:
        """Pack to binary data"""
        return struct.pack('<2f', self.x, self.y)

@dataclass
class Vector3D:
    """3D vector"""
    x: float
    y: float
    z: float
    
    @classmethod
    def unpack(cls, data: bytes, offset: int = 0) -> 'Vector3D':
        """Unpack from binary data"""
        x, y, z = struct.unpack('<3f', data[offset:offset+12])
        return cls(x, y, z)
        
    def pack(self) -> bytes:
        """Pack to binary data"""
        return struct.pack('<3f', self.x, self.y, self.z)

@dataclass
class Quaternion:
    """Quaternion (x, y, z, w)"""
    x: float
    y: float
    z: float
    w: float
    
    @classmethod
    def from_euler(cls, x: float, y: float, z: float) -> 'Quaternion':
        """Create from Euler angles (radians)"""
        cx = math.cos(x * 0.5)
        sx = math.sin(x * 0.5)
        cy = math.cos(y * 0.5)
        sy = math.sin(y * 0.5)
        cz = math.cos(z * 0.5)
        sz = math.sin(z * 0.5)
        
        return cls(
            x=sx * cy * cz - cx * sy * sz,
            y=cx * sy * cz + sx * cy * sz,
            z=cx * cy * sz - sx * sy * cz,
            w=cx * cy * cz + sx * sy * sz
        )
    
    @classmethod
    def unpack(cls, data: bytes, offset: int = 0, compressed: bool = False) -> 'Quaternion':
        """
        Unpack from binary data
        
        Args:
            data: Binary data
            offset: Starting offset
            compressed: Whether quaternion is stored as 16-bit integers
        """
        if compressed:
            # Compressed format: 16-bit integers normalized to [-2048, 2047]
            x, y, z, w = struct.unpack('<4h', data[offset:offset+8])
            return cls(
                x=x / 2048.0,
                y=y / 2048.0,
                z=z / 2048.0,
                w=w / 2048.0
            )
        else:
            # Standard 32-bit float format
            return cls(*struct.unpack('<4f', data[offset:offset+16]))
            
    def pack(self, compressed: bool = False) -> bytes:
        """
        Pack to binary data
        
        Args:
            compressed: Whether to use compressed 16-bit format
        """
        if compressed:
            return struct.pack('<4h',
                int(self.x * 2048),
                int(self.y * 2048),
                int(self.z * 2048),
                int(self.w * 2048)
            )
        return struct.pack('<4f', self.x, self.y, self.z, self.w)

@dataclass
class CAaBox:
    """Axis-aligned bounding box"""
    min: Vector3D
    max: Vector3D
    
    @classmethod
    def unpack(cls, data: bytes, offset: int = 0) -> 'CAaBox':
        """Unpack from binary data"""
        min_x, min_y, min_z = struct.unpack('<3f', data[offset:offset+12])
        max_x, max_y, max_z = struct.unpack('<3f', data[offset+12:offset+24])
        return cls(
            Vector3D(min_x, min_y, min_z),
            Vector3D(max_x, max_y, max_z)
        )
        
    def pack(self) -> bytes:
        """Pack to binary data"""
        return self.min.pack() + self.max.pack()

@dataclass
class RGB:
    """RGB color"""
    r: int
    g: int
    b: int
    
    @classmethod
    def unpack(cls, data: bytes, offset: int = 0) -> 'RGB':
        """Unpack from binary data"""
        r, g, b = struct.unpack('<3B', data[offset:offset+3])
        return cls(r, g, b)
        
    def pack(self) -> bytes:
        """Pack to binary data"""
        return struct.pack('<3B', self.r, self.g, self.b)

@dataclass
class RGBA:
    """RGBA color"""
    r: int
    g: int
    b: int
    a: int
    
    @classmethod
    def unpack(cls, data: bytes, offset: int = 0) -> 'RGBA':
        """Unpack from binary data"""
        r, g, b, a = struct.unpack('<4B', data[offset:offset+4])
        return cls(r, g, b, a)
        
    def pack(self) -> bytes:
        """Pack to binary data"""
        return struct.pack('<4B', self.r, self.g, self.b, self.a)

def read_fixed_point(data: bytes, offset: int = 0, bits: int = 16) -> float:
    """
    Read fixed-point number
    
    Args:
        data: Binary data
        offset: Starting offset
        bits: Number of bits for fractional part
        
    Returns:
        Float value
    """
    if bits == 16:
        value = struct.unpack('<I', data[offset:offset+4])[0]
        return value / 65536.0
    elif bits == 8:
        value = struct.unpack('<H', data[offset:offset+2])[0]
        return value / 256.0
    else:
        raise ValueError(f"Unsupported fixed-point format: {bits} bits")

def pack_fixed_point(value: float, bits: int = 16) -> bytes:
    """
    Pack fixed-point number
    
    Args:
        value: Float value
        bits: Number of bits for fractional part
        
    Returns:
        Packed bytes
    """
    if bits == 16:
        return struct.pack('<I', int(value * 65536))
    elif bits == 8:
        return struct.pack('<H', int(value * 256))
    else:
        raise ValueError(f"Unsupported fixed-point format: {bits} bits")

def read_packed_bits(data: bytes, offset: int, bit_count: int) -> List[bool]:
    """
    Read packed bit values
    
    Args:
        data: Binary data
        offset: Starting offset
        bit_count: Number of bits to read
        
    Returns:
        List of boolean values
    """
    result = []
    byte_count = (bit_count + 7) // 8
    value = int.from_bytes(data[offset:offset+byte_count], 'little')
    
    for i in range(bit_count):
        result.append(bool(value & (1 << i)))
    
    return result

def pack_bits(values: List[bool]) -> bytes:
    """
    Pack bit values
    
    Args:
        values: List of boolean values
        
    Returns:
        Packed bytes
    """
    if not values:
        return b''
        
    result = 0
    for i, value in enumerate(values):
        if value:
            result |= (1 << i)
            
    byte_count = (len(values) + 7) // 8
    return result.to_bytes(byte_count, 'little')

def read_cstring(data: bytes, offset: int = 0, max_length: Optional[int] = None) -> Tuple[str, int]:
    """
    Read null-terminated string
    
    Args:
        data: Binary data
        offset: Starting offset
        max_length: Maximum string length (optional)
        
    Returns:
        Tuple of (string, new offset)
    """
    end = data.find(b'\0', offset)
    if end == -1:
        if max_length:
            end = min(offset + max_length, len(data))
        else:
            end = len(data)
            
    string = data[offset:end].decode('utf-8', errors='replace')
    return string, end + 1

def pack_cstring(text: str) -> bytes:
    """
    Pack null-terminated string
    
    Args:
        text: String to pack
        
    Returns:
        Packed bytes including null terminator
    """
    return text.encode('utf-8') + b'\0'