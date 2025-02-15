from typing import Dict, Any, List
from ..base import BaseChunk, ChunkParsingError
from .header import Mh2oLayerHeader
from .layer import Mh2oLayer

class Mh2oChunk(BaseChunk):
    """MH2O (Water Data) chunk parser.
    
    Contains water level information and vertex data.
    Structure is more complex than most chunks, with headers
    pointing to additional data sections.
    
    Each chunk can contain up to 8 water layers, each with:
    - Header (16 bytes)
    - Optional vertex height data
    - Optional render flags
    """
    
    MAX_LAYERS = 8
    HEADER_SIZE = MAX_LAYERS * 16  # 8 layers possible, 16 bytes each
    
    def parse(self) -> Dict[str, Any]:
        """Parse MH2O chunk data.
        
        Returns:
            Dictionary containing:
            - layers: List of water layer data
            - count: Number of water layers
            
        Each layer contains:
        - layer_index: Index of this layer (0-7)
        - height_level: Base water level
        - is_fishable: Whether water is fishable
        - is_fatigue: Whether water causes fatigue
        - dimensions: (width, height) if has vertex data
        - vertices: List of vertex heights if present
        - render_flags: List of render flags if present
        """
        if len(self.data) < self.HEADER_SIZE:
            raise ChunkParsingError(
                f"MH2O chunk too small: {len(self.data)} < {self.HEADER_SIZE}"
            )
        
        layers = []
        offset = 0
        
        # Parse up to 8 water layers
        for i in range(self.MAX_LAYERS):
            try:
                # Read layer header
                header = Mh2oLayerHeader.from_bytes(self.data[offset:offset + 16])
                
                if header.info_mask == 0:  # No water in this layer
                    offset += 16
                    continue
                
                width, height = header.dimensions
                layer = Mh2oLayer(
                    layer_index=i,
                    height_level=header.height_level,
                    is_fishable=header.is_fishable,
                    is_fatigue=header.is_fatigue,
                    dimensions=(width, height) if header.has_vertices else None
                )
                
                # Parse vertex data if present
                if header.has_vertices and header.vertex_offset:
                    layer.vertices = Mh2oLayer.parse_vertex_data(
                        self.data, header.vertex_offset, width, height
                    )
                
                # Parse render flags if present
                if header.has_render_flags and header.render_offset:
                    layer.render_flags = Mh2oLayer.parse_render_flags(
                        self.data, header.render_offset, width, height
                    )
                
                layers.append(layer.to_dict())
                
            except Exception as e:
                raise ChunkParsingError(f"Failed to parse MH2O layer {i}: {e}")
            
            offset += 16  # Move to next layer header
        
        return {
            'layers': layers,
            'count': len(layers)
        }