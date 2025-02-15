from typing import Dict, Any, List
import struct
from ..base import BaseChunk, ChunkParsingError

class McnrChunk(BaseChunk):
    """MCNR (Normal Map) chunk parser.
    
    Contains normal vectors for terrain vertices.
    Each normal is 3 signed bytes (8-bit values).
    """
    
    VERTICES_COUNT = 145  # Same as MCVT
    ENTRY_SIZE = 3  # 3 bytes per normal
    EXPECTED_SIZE = VERTICES_COUNT * ENTRY_SIZE
    
    def parse(self) -> Dict[str, Any]:
        """Parse MCNR chunk data."""
        if len(self.data) != self.EXPECTED_SIZE:
            raise ChunkParsingError(
                f"MCNR chunk size {len(self.data)} != {self.EXPECTED_SIZE}"
            )
        
        normals = []
        for i in range(self.VERTICES_COUNT):
            offset = i * self.ENTRY_SIZE
            # Convert signed bytes to floats (-127 to 127 -> -1 to 1)
            nx = struct.unpack('b', self.data[offset:offset+1])[0] / 127.0
            ny = struct.unpack('b', self.data[offset+1:offset+2])[0] / 127.0
            nz = struct.unpack('b', self.data[offset+2:offset+3])[0] / 127.0
            normals.append((nx, ny, nz))
        
        return {
            'normals': normals,
            'count': self.VERTICES_COUNT
        }