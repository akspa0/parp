from typing import Dict, Any, List
import struct
from ..base import BaseChunk, ChunkParsingError
from .entry import MclyEntry

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
            texture_id, flags, mcal_offset, effect_id = struct.unpack('<4I', entry_data)
            
            entry = MclyEntry(
                texture_id=texture_id,
                flags=flags,
                mcal_offset=mcal_offset,
                effect_id=effect_id
            )
            entries.append(entry.to_dict())
        
        return {
            'layers': entries,
            'count': count
        }