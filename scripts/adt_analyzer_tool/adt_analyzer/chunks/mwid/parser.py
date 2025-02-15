"""MWID (WMO Indices) chunk parser."""
from typing import Dict, Any, List
import struct
from ..base import BaseChunk, ChunkParsingError

class MwidChunk(BaseChunk):
    """MWID chunk parser.
    
    Contains offsets into the MWMO chunk for WMO filenames.
    Each entry is a uint32 offset.
    """
    
    def parse(self) -> Dict[str, Any]:
        """Parse MWID chunk data.
        
        Returns:
            Dictionary containing:
            - offsets: List of uint32 offsets into MWMO chunk
            - count: Number of offsets
        """
        if len(self.data) % 4 != 0:
            raise ChunkParsingError(
                f"MWID chunk size {len(self.data)} not divisible by 4"
            )
        
        count = len(self.data) // 4
        offsets = list(struct.unpack(f'<{count}I', self.data))
        
        return {
            'offsets': offsets,
            'count': count
        }
