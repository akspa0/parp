from typing import Dict, Any, List
import struct
from ..base import BaseChunk, ChunkParsingError

class MclvChunk(BaseChunk):
    """MCLV (Light Values) chunk parser.
    
    Contains light information for the terrain.
    Used for legacy lighting system.
    Each value is a 32-bit color value.
    """
    
    ENTRY_SIZE = 4  # 4 bytes per light value
    
    def parse(self) -> Dict[str, Any]:
        """Parse MCLV chunk data.
        
        Returns:
            Dictionary containing:
            - light_values: List of 32-bit color values
            - count: Number of light values
            
        Note:
            Unlike MCCV/MCVT, the number of entries is not fixed
            and depends on the chunk size.
        """
        if len(self.data) % self.ENTRY_SIZE != 0:
            raise ChunkParsingError(
                f"MCLV chunk size {len(self.data)} not divisible by {self.ENTRY_SIZE}"
            )
        
        count = len(self.data) // self.ENTRY_SIZE
        values = []
        
        try:
            for i in range(count):
                offset = i * self.ENTRY_SIZE
                color_value = struct.unpack('<I', self.data[offset:offset+self.ENTRY_SIZE])[0]
                values.append(color_value)
            
            return {
                'light_values': values,
                'count': count
            }
            
        except struct.error as e:
            raise ChunkParsingError(f"Failed to parse MCLV data: {e}")