# adt_analyzer/chunks/mccv.py
from typing import Dict, Any, List
import struct
from .base import BaseChunk, ChunkParsingError

class MccvChunk(BaseChunk):
    """MCCV (Vertex Colors) chunk parser.
    
    Contains vertex colors for the terrain.
    Each color is 4 bytes (BGRA).
    """
    
    VERTICES_COUNT = 145  # Same as MCVT
    ENTRY_SIZE = 4  # 4 bytes per color (BGRA)
    EXPECTED_SIZE = VERTICES_COUNT * ENTRY_SIZE
    
    def parse(self) -> Dict[str, Any]:
        """Parse MCCV chunk data."""
        if len(self.data) != self.EXPECTED_SIZE:
            raise ChunkParsingError(
                f"MCCV chunk size {len(self.data)} != {self.EXPECTED_SIZE}"
            )
        
        colors = []
        for i in range(self.VERTICES_COUNT):
            offset = i * self.ENTRY_SIZE
            b, g, r, a = struct.unpack('4B', self.data[offset:offset+4])
            colors.append((r, g, b, a))
        
        return {
            'colors': colors,
            'count': self.VERTICES_COUNT
        }
