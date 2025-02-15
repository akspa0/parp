from typing import Dict, Any, List
from ..base import BaseChunk, ChunkParsingError
from .entry import McseEntry

class McseChunk(BaseChunk):
    """MCSE (Sound Emitters) chunk parser.
    
    Contains sound emitter definitions for the map chunk.
    Each emitter is 28 bytes and defines properties of a sound source.
    """
    
    ENTRY_SIZE = 28  # Size of each sound emitter entry
    
    def parse(self) -> Dict[str, Any]:
        """Parse MCSE chunk data.
        
        Returns:
            Dictionary containing:
            - emitters: List of sound emitter entries
            - count: Number of emitters
            
        Each emitter contains:
        - sound_id: Sound effect identifier
        - sound_type: Type of sound
        - position: (x, y, z) coordinates
        - min_distance: Minimum audible distance
        - max_distance: Maximum audible distance
        """
        if len(self.data) % self.ENTRY_SIZE != 0:
            raise ChunkParsingError(
                f"MCSE chunk size {len(self.data)} not divisible by {self.ENTRY_SIZE}"
            )
        
        count = len(self.data) // self.ENTRY_SIZE
        emitters = []
        
        for i in range(count):
            try:
                entry_data = self.data[i*self.ENTRY_SIZE:(i+1)*self.ENTRY_SIZE]
                entry = McseEntry.from_bytes(entry_data)
                emitters.append(entry.to_dict())
                
            except Exception as e:
                raise ChunkParsingError(f"Failed to parse MCSE emitter {i}: {e}")
        
        return {
            'emitters': emitters,
            'count': count
        }