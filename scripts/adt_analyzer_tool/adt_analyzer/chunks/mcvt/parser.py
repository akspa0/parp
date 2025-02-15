from typing import Dict, Any, List
import struct
from ..base import BaseChunk, ChunkParsingError

class McvtChunk(BaseChunk):
    """MCVT (Height Map) chunk parser.
    
    Contains height information for the terrain.
    9x9 + 8x8 = 145 vertices total
    Each height is a 32-bit float.
    """
    
    VERTICES_COUNT = 145  # (9*9 + 8*8)
    EXPECTED_SIZE = VERTICES_COUNT * 4  # 4 bytes per float
    
    def parse(self) -> Dict[str, Any]:
        """Parse MCVT chunk data."""
        if len(self.data) != self.EXPECTED_SIZE:
            raise ChunkParsingError(
                f"MCVT chunk size {len(self.data)} != {self.EXPECTED_SIZE}"
            )
        
        heights = struct.unpack(f'<{self.VERTICES_COUNT}f', self.data)
        
        return {
            'heights': list(heights),
            'count': self.VERTICES_COUNT
        }