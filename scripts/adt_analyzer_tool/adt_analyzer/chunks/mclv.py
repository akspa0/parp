# adt_analyzer/chunks/mclv.py
from typing import Dict, Any, List
import struct
from .base import BaseChunk, ChunkParsingError

class MclvChunk(BaseChunk):
    """MCLV (Light Values) chunk parser.
    
    Contains light information for the terrain.
    Used for legacy lighting.
    """
    
    def parse(self) -> Dict[str, Any]:
        """Parse MCLV chunk data."""
        if len(self.data) % 4 != 0:
            raise ChunkParsingError(f"MCLV chunk size {len(self.data)} not divisible by 4")
        
        count = len(self.data) // 4
        values = []
        
        try:
            for i in range(count):
                offset = i * 4
                color_value = struct.unpack('<I', self.data[offset:offset+4])[0]
                values.append(color_value)
            
            return {
                'light_values': values,
                'count': count
            }
            
        except struct.error as e:
            raise ChunkParsingError(f"Failed to parse MCLV data: {e}")
