# adt_analyzer/chunks/mh2o.py
from typing import Dict, Any, List, Optional
import struct
from .base import BaseChunk, ChunkParsingError

class Mh2oChunk(BaseChunk):
    """MH2O (Water Data) chunk parser.
    
    Contains water level information and vertex data.
    Structure is more complex than most chunks, with headers
    pointing to additional data sections.
    """
    
    HEADER_SIZE = 8 * 8  # 8 layers possible, 8 bytes each
    
    def _parse_vertex_data(self, data: bytes, offset: int, width: int, height: int) -> List[float]:
        """Parse water vertex height data."""
        count = width * height
        try:
            heights = struct.unpack(f'<{count}f', data[offset:offset + count * 4])
            return list(heights)
        except struct.error as e:
            raise ChunkParsingError(f"Failed to parse water vertex data: {e}")

    def _parse_render_flags(self, data: bytes, offset: int, width: int, height: int) -> List[int]:
        """Parse water render flags."""
        count = width * height
        try:
            flags = struct.unpack(f'<{count}B', data[offset:offset + count])
            return list(flags)
        except struct.error as e:
            raise ChunkParsingError(f"Failed to parse water render flags: {e}")
    
    def parse(self) -> Dict[str, Any]:
        """Parse MH2O chunk data."""
        if len(self.data) < self.HEADER_SIZE:
            raise ChunkParsingError(f"MH2O chunk too small: {len(self.data)} < {self.HEADER_SIZE}")
        
        layers = []
        offset = 0
        
        # Parse up to 8 water layers
        for i in range(8):
            try:
                # Read layer header
                (info_mask, height_level,
                 offset_vertex, offset_render) = struct.unpack('<2I2I', 
                    self.data[offset:offset + 16])
                
                if info_mask == 0:  # No water in this layer
                    continue
                
                # Extract information from info_mask
                has_vertices = (info_mask & 1) != 0
                has_render_flags = (info_mask & 2) != 0
                is_fishable = (info_mask & 4) != 0
                is_fatigue = (info_mask & 8) != 0
                
                layer_data = {
                    'layer_index': i,
                    'height_level': height_level,
                    'is_fishable': is_fishable,
                    'is_fatigue': is_fatigue,
                    'vertices': None,
                    'render_flags': None
                }
                
                # Parse vertex data if present
                if has_vertices and offset_vertex:
                    # Get dimensions from info_mask
                    width = ((info_mask >> 16) & 0xFF) + 1
                    height = ((info_mask >> 24) & 0xFF) + 1
                    layer_data['vertices'] = self._parse_vertex_data(
                        self.data, offset_vertex, width, height
                    )
                    layer_data['dimensions'] = (width, height)
                
                # Parse render flags if present
                if has_render_flags and offset_render:
                    width = ((info_mask >> 16) & 0xFF) + 1
                    height = ((info_mask >> 24) & 0xFF) + 1
                    layer_data['render_flags'] = self._parse_render_flags(
                        self.data, offset_render, width, height
                    )
                
                layers.append(layer_data)
                
            except struct.error as e:
                raise ChunkParsingError(f"Failed to parse MH2O layer {i}: {e}")
            
            offset += 16  # Move to next layer header
        
        return {
            'layers': layers,
            'count': len(layers)
        }
