# adt_analyzer/chunks/mcrf.py
from typing import Dict, Any, List
import struct
from .base import BaseChunk, ChunkParsingError

class McrfChunk(BaseChunk):
    """MCRF (Doodad References) chunk parser.
    
    Contains references to M2/WMO models placed in this map chunk.
    Each entry is a uint32 index.
    """
    
    def parse(self) -> Dict[str, Any]:
        """Parse MCRF chunk data."""
        if len(self.data) % 4 != 0:
            raise ChunkParsingError(f"MCRF chunk size {len(self.data)} not divisible by 4")
        
        count = len(self.data) // 4
        indices = struct.unpack(f'<{count}I', self.data)
        
        return {
            'doodad_refs': list(indices),
            'count': count
        }
