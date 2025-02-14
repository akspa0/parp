# adt_analyzer/chunks/mddf/entry.py
from dataclasses import dataclass
from typing import Tuple
import struct

@dataclass
class MddfEntry:
    """Single entry in MDDF chunk defining M2 model placement."""
    mmid_entry: int      # Index into MMID/MMDX
    unique_id: int       # Unique identifier
    position: Tuple[float, float, float]  # (x, y, z)
    rotation: Tuple[float, float, float]  # (x, y, z) in radians
    scale: float        # Model scale (16-bit fixed point, divide by 1024)
    flags: int          # Placement flags

    @classmethod
    def from_bytes(cls, data: bytes) -> 'MddfEntry':
        """Parse a single MDDF entry from bytes."""
        mmid_entry, unique_id = struct.unpack('<2I', data[0:8])
        position = struct.unpack('<3f', data[8:20])
        rotation = struct.unpack('<3f', data[20:32])
        scale, flags = struct.unpack('<HH', data[32:36])
        
        return cls(
            mmid_entry=mmid_entry,
            unique_id=unique_id,
            position=position,
            rotation=rotation,
            scale=scale / 1024.0,  # Convert from fixed point
            flags=flags
        )

    def to_dict(self) -> dict:
        """Convert entry to dictionary format."""
        return {
            'mmid_entry': self.mmid_entry,
            'unique_id': self.unique_id,
            'position': {
                'x': self.position[0],
                'y': self.position[1],
                'z': self.position[2]
            },
            'rotation': {
                'x': self.rotation[0],
                'y': self.rotation[1],
                'z': self.rotation[2]
            },
            'scale': self.scale,
            'flags': self.flags
        }
