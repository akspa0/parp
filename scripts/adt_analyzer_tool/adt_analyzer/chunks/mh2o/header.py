from dataclasses import dataclass
from typing import Dict, Tuple

@dataclass
class Mh2oLayerHeader:
    """MH2O (Water Data) layer header.
    
    Each layer header is 16 bytes and contains information about
    a potential water layer in the chunk.
    """
    info_mask: int        # Bitfield containing flags and dimensions
    height_level: int     # Base water level
    vertex_offset: int    # Offset to vertex data (if present)
    render_offset: int    # Offset to render flags (if present)

    @property
    def has_vertices(self) -> bool:
        """Whether this layer has vertex data."""
        return (self.info_mask & 1) != 0

    @property
    def has_render_flags(self) -> bool:
        """Whether this layer has render flags."""
        return (self.info_mask & 2) != 0

    @property
    def is_fishable(self) -> bool:
        """Whether this water is fishable."""
        return (self.info_mask & 4) != 0

    @property
    def is_fatigue(self) -> bool:
        """Whether this water causes fatigue."""
        return (self.info_mask & 8) != 0

    @property
    def dimensions(self) -> Tuple[int, int]:
        """Get width and height from info_mask."""
        width = ((self.info_mask >> 16) & 0xFF) + 1
        height = ((self.info_mask >> 24) & 0xFF) + 1
        return (width, height)

    @classmethod
    def from_bytes(cls, data: bytes) -> 'Mh2oLayerHeader':
        """Create header from bytes."""
        import struct
        info_mask, height_level, vertex_offset, render_offset = struct.unpack(
            '<2I2I', data[:16]
        )
        return cls(
            info_mask=info_mask,
            height_level=height_level,
            vertex_offset=vertex_offset,
            render_offset=render_offset
        )

    def to_dict(self) -> Dict:
        """Convert header to dictionary."""
        width, height = self.dimensions
        return {
            'has_vertices': self.has_vertices,
            'has_render_flags': self.has_render_flags,
            'is_fishable': self.is_fishable,
            'is_fatigue': self.is_fatigue,
            'height_level': self.height_level,
            'dimensions': (width, height)
        }