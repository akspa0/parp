# adt_analyzer/chunks/modf.py
from typing import Dict, Any
import struct
from .base import BaseChunk, ChunkParsingError

class ModfChunk(BaseChunk):
    """MODF (WMO Placement) chunk parser.
    
    Contains information about WMO model placement in the map.
    Each entry is 64 bytes.
    """
    
    ENTRY_SIZE = 64
    
    def parse(self) -> Dict[str, Any]:
        """Parse MODF chunk data."""
        if len(self.data) % self.ENTRY_SIZE != 0:
            raise ChunkParsingError(
                f"MODF chunk size {len(self.data)} not divisible by {self.ENTRY_SIZE}"
            )
        
        count = len(self.data) // self.ENTRY_SIZE
        entries = []
        
        for i in range(count):
            entry_data = self.data[i*self.ENTRY_SIZE:(i+1)*self.ENTRY_SIZE]
            
            # Unpack the entry
            (mwid_entry, unique_id,
             pos_x, pos_y, pos_z,
             rot_x, rot_y, rot_z,
             bounds_min_x, bounds_min_y, bounds_min_z,
             bounds_max_x, bounds_max_y, bounds_max_z,
             flags, doodad_set, name_set, scale) = struct.unpack('<2I6f6f4H', entry_data)
            
            entries.append({
                'mwid_entry': mwid_entry,
                'unique_id': unique_id,
                'position': (pos_x, pos_y, pos_z),
                'rotation': (rot_x, rot_y, rot_z),
                'bounds_min': (bounds_min_x, bounds_min_y, bounds_min_z),
                'bounds_max': (bounds_max_x, bounds_max_y, bounds_max_z),
                'flags': flags,
                'doodad_set': doodad_set,
                'name_set': name_set,
                'scale': scale / 1024.0  # Scale is stored as fixed-point
            })
        
        return {
            'entries': entries,
            'count': count
        }
