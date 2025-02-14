# adt_analyzer/chunks/mwid.py
from typing import Dict, Any
import struct
from .base import BaseChunk, ChunkParsingError

class MwidChunk(BaseChunk):
    """MWID (WMO Offset) chunk parser.
    
    Contains offsets into the MWMO chunk for WMO filenames.
    Each entry is a uint32 offset.
    """
    
    def parse(self) -> Dict[str, Any]:
        """Parse MWID chunk data."""
        if len(self.data) % 4 != 0:
            raise ChunkParsingError(f"MWID chunk size {len(self.data)} not divisible by 4")
        
        count = len(self.data) // 4
        offsets = struct.unpack(f'<{count}I', self.data)
        
        return {
            'offsets': list(offsets),
            'count': count
        }