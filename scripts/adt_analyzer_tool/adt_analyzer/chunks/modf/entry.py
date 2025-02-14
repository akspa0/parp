# adt_analyzer/chunks/modf/entry.py
from dataclasses import dataclass
from typing import Tuple
import struct

@dataclass
class ModfEntry:
    """Single entry in MODF chunk defining WMO placement."""
    mwid_entry: int      # Index into MWID/MWMO
    unique_id: int       # Unique identifier
    position: Tuple[float, float, float]  # (x, y, z)
    rotation: Tuple[float, float, float]  # (x, y, z) in radians
    bounds_min: Tuple[float, float, float]  # Minimum bounds
    bounds_max: Tuple[float, float, float]  # Maximum bounds
    flags: int          # Placement flags
    doodad_set: int     # Doodad set index
    name_set: int       # Name set index
    scale: float        # Model scale (16-bit fixed point, divide by 1024)

    @classmethod
    def from_bytes(cls, data: bytes) -> 'ModfEntry':
        """Parse a single MODF entry from bytes."""
        mwid_entry, unique_id = struct.unpack('<2I', data[0:8])
        position = struct.unpack('<3f', data[8:20])
        rotation = struct.unpack('<3f', data[20:32])
        bounds_min = struct.unpack('<3f', data[32:44])
        bounds_max = struct.unpack('<3f', data[44:56])
        flags, doodad_set, name_set, scale = struct.unpack('<4H', data[56:64])
        
        return cls(
            mwid_entry=mwid_entry,
            unique_id=unique_id,
            position=position,
            rotation=rotation,
            bounds_min=bounds_min,
            bounds_max=bounds_max,
            flags=flags,
            doodad_set=doodad_set,
            name_set=name_set,
            scale=scale / 1024.0  # Convert from fixed point
        )

    def to_dict(self) -> dict:
        """Convert entry to dictionary format."""
        return {
            'mwid_entry': self.mwid_entry,
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
            'bounds': {
                'min': {
                    'x': self.bounds_min[0],
                    'y': self.bounds_min[1],
                    'z': self.bounds_min[2]
                },
                'max': {
                    'x': self.bounds_max[0],
                    'y': self.bounds_max[1],
                    'z': self.bounds_max[2]
                }
            },
            'flags': self.flags,
            'doodad_set': self.doodad_set,
            'name_set': self.name_set,
            'scale': self.scale
        }
