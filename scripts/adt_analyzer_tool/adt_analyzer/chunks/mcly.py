# adt_analyzer/chunks/mcly.py
from typing import Dict, Any, List
import struct
from .base import BaseChunk, ChunkParsingError

class MclyChunk(BaseChunk):
    """MCLY (Texture Layer) chunk parser.
    
    Contains information about texture layers.
    Each entry is 16 bytes.
    """
    
    ENTRY_SIZE = 16
    
    def parse(self) -> Dict[str, Any]:
        """Parse MCLY chunk data."""
        if len(self.data) % self.ENTRY_SIZE != 0:
            raise ChunkParsingError(
                f"MCLY chunk size {len(self.data)} not divisible by {self.ENTRY_SIZE}"
            )
        
        count = len(self.data) // self.ENTRY_SIZE
        entries = []
        
        for i in range(count):
            entry_data = self.data[i*self.ENTRY_SIZE:(i+1)*self.ENTRY_SIZE]
            
            # Unpack the entry
            (textureId, flags, offsetInMCAL, effectId) = struct.unpack('<4I', entry_data)
            
            entries.append({
                'texture_id': textureId,
                'flags': flags,
                'mcal_offset': offsetInMCAL,
                'effect_id': effectId
            })
        
        return {
            'layers': entries,
            'count': count
        }
