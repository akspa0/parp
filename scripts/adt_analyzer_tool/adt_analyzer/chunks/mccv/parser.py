from typing import Dict, Any, List, Tuple
import struct
from ..base import BaseChunk, ChunkParsingError

class MccvChunk(BaseChunk):
    """MCCV (Vertex Colors) chunk parser.
    
    Contains vertex colors for the terrain.
    Each color is 4 bytes (BGRA).
    Corresponds to the same vertices as MCVT chunk.
    """
    
    VERTICES_COUNT = 145  # Same as MCVT (9*9 + 8*8)
    ENTRY_SIZE = 4  # 4 bytes per color (BGRA)
    EXPECTED_SIZE = VERTICES_COUNT * ENTRY_SIZE
    
    def parse(self) -> Dict[str, Any]:
        """Parse MCCV chunk data.
        
        Returns:
            Dictionary containing:
            - colors: List of RGBA tuples (values 0-255)
            - count: Number of vertex colors (always 145)
        """
        if len(self.data) != self.EXPECTED_SIZE:
            raise ChunkParsingError(
                f"MCCV chunk size {len(self.data)} != {self.EXPECTED_SIZE}"
            )
        
        colors: List[Tuple[int, int, int, int]] = []
        for i in range(self.VERTICES_COUNT):
            offset = i * self.ENTRY_SIZE
            # Data is stored as BGRA, but we convert to RGBA for consistency
            b, g, r, a = struct.unpack('4B', self.data[offset:offset+4])
            colors.append((r, g, b, a))
        
        return {
            'colors': colors,
            'count': self.VERTICES_COUNT
        }