from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import struct
from ..base import ChunkParsingError

@dataclass
class Mh2oLayer:
    """MH2O (Water Data) layer.
    
    Represents a single water layer with optional vertex heights
    and render flags.
    """
    layer_index: int
    height_level: int
    is_fishable: bool
    is_fatigue: bool
    dimensions: Optional[Tuple[int, int]] = None
    vertices: Optional[List[float]] = None
    render_flags: Optional[List[int]] = None

    @classmethod
    def parse_vertex_data(cls, data: bytes, offset: int, width: int, height: int) -> List[float]:
        """Parse water vertex height data.
        
        Args:
            data: Raw chunk data
            offset: Offset to vertex data
            width: Width of water grid
            height: Height of water grid
            
        Returns:
            List of vertex heights as floats
        """
        count = width * height
        try:
            heights = struct.unpack(f'<{count}f', data[offset:offset + count * 4])
            return list(heights)
        except struct.error as e:
            raise ChunkParsingError(f"Failed to parse water vertex data: {e}")

    @classmethod
    def parse_render_flags(cls, data: bytes, offset: int, width: int, height: int) -> List[int]:
        """Parse water render flags.
        
        Args:
            data: Raw chunk data
            offset: Offset to render flags
            width: Width of water grid
            height: Height of water grid
            
        Returns:
            List of render flags as integers
        """
        count = width * height
        try:
            flags = struct.unpack(f'<{count}B', data[offset:offset + count])
            return list(flags)
        except struct.error as e:
            raise ChunkParsingError(f"Failed to parse water render flags: {e}")

    def to_dict(self) -> Dict:
        """Convert layer to dictionary."""
        return {
            'layer_index': self.layer_index,
            'height_level': self.height_level,
            'is_fishable': self.is_fishable,
            'is_fatigue': self.is_fatigue,
            'dimensions': self.dimensions,
            'vertices': self.vertices,
            'render_flags': self.render_flags
        }