# adt_analyzer/chunks/mddf.py
from typing import Dict, Any, List
import struct
from .base import BaseChunk, ChunkParsingError

class MddfChunk(BaseChunk):
    """MDDF (M2 Model Placement) chunk parser.
    
    Contains information about M2 model placement in the map.
    Each entry is 36 bytes.
    """
    
    ENTRY_SIZE = 36
    
    def parse(self) -> Dict[str, Any]:
        """Parse MDDF chunk data."""
        if len(self.data) % self.ENTRY_SIZE != 0:
            raise ChunkParsingError(
                f"MDDF chunk size {len(self.data)} not divisible by {self.ENTRY_SIZE}"
            )
        
        count = len(self.data) // self.ENTRY_SIZE
        entries = []
        
        for i in range(count):
            entry_data = self.data[i*self.ENTRY_SIZE:(i+1)*self.ENTRY_SIZE]
            
            # Unpack the entry
            (mmid_entry, unique_id,
             pos_x, pos_y, pos_z,
             rot_x, rot_y, rot_z,
             scale, flags) = struct.unpack('<2I6fHH', entry_data)
            
            entries.append({
                'mmid_entry': mmid_entry,
                'unique_id': unique_id,
                'position': (pos_x, pos_y, pos_z),
                'rotation': (rot_x, rot_y, rot_z),
                'scale': scale / 1024.0,  # Scale is stored as fixed-point
                'flags': flags
            })
        
        return {
            'entries': entries,
            'count': count
        }
