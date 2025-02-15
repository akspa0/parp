from typing import Dict, Any, List
import struct
from ..base import BaseChunk, ChunkParsingError

class McrfChunk(BaseChunk):
    """MCRF (Doodad References) chunk parser.
    
    Contains references to M2/WMO models placed in this map chunk.
    Each entry is a uint32 index that references entries in the MDDF/MODF chunks.
    """
    
    ENTRY_SIZE = 4  # uint32
    
    def parse(self) -> Dict[str, Any]:
        """Parse MCRF chunk data.
        
        Returns:
            Dictionary containing:
            - doodad_refs: List of indices into MDDF/MODF chunks
            - count: Number of references
            
        Note:
            These indices reference the combined set of M2/WMO placements
            from both MDDF and MODF chunks.
        """
        if len(self.data) % self.ENTRY_SIZE != 0:
            raise ChunkParsingError(
                f"MCRF chunk size {len(self.data)} not divisible by {self.ENTRY_SIZE}"
            )
        
        count = len(self.data) // self.ENTRY_SIZE
        indices = struct.unpack(f'<{count}I', self.data)
        
        return {
            'doodad_refs': list(indices),
            'count': count
        }