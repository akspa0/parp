# adt_analyzer/chunks/mcse.py
from typing import Dict, Any, List
import struct
from .base import BaseChunk, ChunkParsingError

class McseChunk(BaseChunk):
    """MCSE (Sound Emitters) chunk parser.
    
    Contains sound emitter definitions for the map chunk.
    Each emitter is 28 bytes.
    """
    
    ENTRY_SIZE = 28
    
    def parse(self) -> Dict[str, Any]:
        """Parse MCSE chunk data."""
        if len(self.data) % self.ENTRY_SIZE != 0:
            raise ChunkParsingError(
                f"MCSE chunk size {len(self.data)} not divisible by {self.ENTRY_SIZE}"
            )
        
        count = len(self.data) // self.ENTRY_SIZE
        emitters = []
        
        for i in range(count):
            entry_data = self.data[i*self.ENTRY_SIZE:(i+1)*self.ENTRY_SIZE]
            
            try:
                # Unpack the emitter data
                (sound_id, sound_type, pos_x, pos_y, pos_z,
                 min_distance, max_distance) = struct.unpack('<2I3f2f', entry_data)
                
                emitters.append({
                    'sound_id': sound_id,
                    'sound_type': sound_type,
                    'position': (pos_x, pos_y, pos_z),
                    'min_distance': min_distance,
                    'max_distance': max_distance
                })
                
            except struct.error as e:
                raise ChunkParsingError(f"Failed to parse MCSE emitter {i}: {e}")
        
        return {
            'emitters': emitters,
            'count': count
        }
