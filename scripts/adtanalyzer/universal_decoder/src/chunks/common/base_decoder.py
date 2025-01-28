"""
Base class for chunk decoders
"""

from typing import Dict, Any, Tuple
from dataclasses import dataclass
import struct

@dataclass
class Vector3D:
    x: float
    y: float
    z: float

    @classmethod
    def from_bytes(cls, data: bytes, offset: int = 0) -> 'Vector3D':
        """Create Vector3D from binary data"""
        x, y, z = struct.unpack('<fff', data[offset:offset+12])
        return cls(x, y, z)

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for JSON output"""
        return {
            'x': self.x,
            'y': self.y,
            'z': self.z
        }

class ChunkDecoder:
    """Base class for all chunk decoders"""

    def __init__(self, name: bytes):
        self.name = name

    def decode(self, data: bytes) -> Dict[str, Any]:
        """
        Decode chunk data into a dictionary
        
        Args:
            data: Raw chunk data (without chunk header)
            
        Returns:
            Dictionary containing decoded data
        """
        raise NotImplementedError("Chunk decoders must implement decode method")

    def encode(self, data: Dict[str, Any]) -> bytes:
        """
        Encode dictionary data back into chunk format
        
        Args:
            data: Dictionary containing chunk data
            
        Returns:
            Raw chunk data (without chunk header)
        """
        raise NotImplementedError("Chunk decoders must implement encode method")

    @staticmethod
    def read_padded_string(data: bytes, offset: int = 0) -> Tuple[str, int]:
        """
        Read null-terminated string from data
        
        Returns:
            Tuple of (string, next_offset)
        """
        end = data.find(b'\0', offset)
        if end == -1:
            return data[offset:].decode('utf-8', 'replace'), len(data)
        return data[offset:end].decode('utf-8', 'replace'), end + 1

    @staticmethod
    def read_fixed_string(data: bytes, size: int, offset: int = 0) -> str:
        """Read fixed-size string, trimming null termination"""
        return data[offset:offset+size].split(b'\0', 1)[0].decode('utf-8', 'replace')

    @staticmethod
    def read_vec3d(data: bytes, offset: int = 0) -> Vector3D:
        """Read 3D vector"""
        return Vector3D.from_bytes(data, offset)

    @staticmethod
    def read_vec2d(data: bytes, offset: int = 0) -> Tuple[float, float]:
        """Read 2D vector"""
        return struct.unpack('<ff', data[offset:offset+8])

    @staticmethod
    def pack_vec3d(vec: Vector3D) -> bytes:
        """Pack Vector3D into bytes"""
        return struct.pack('<fff', vec.x, vec.y, vec.z)

    @staticmethod
    def pack_string(s: str, fixed_size: int = None) -> bytes:
        """
        Pack string into bytes
        
        Args:
            s: String to pack
            fixed_size: If provided, pad/truncate to this size
            
        Returns:
            Packed bytes including null termination
        """
        encoded = s.encode('utf-8') + b'\0'
        if fixed_size is not None:
            if len(encoded) > fixed_size:
                encoded = encoded[:fixed_size-1] + b'\0'
            else:
                encoded = encoded.ljust(fixed_size, b'\0')
        return encoded

    def create_chunk(self, data: bytes) -> bytes:
        """Create full chunk including header"""
        return self.name + struct.pack('<I', len(data)) + data

    def validate_size(self, data: bytes, expected_size: int) -> None:
        """Validate chunk data size"""
        if len(data) != expected_size:
            raise ValueError(
                f"Invalid chunk size for {self.name}: "
                f"expected {expected_size}, got {len(data)}"
            )