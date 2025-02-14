# adt_analyzer/chunks/mmid.py
from typing import Dict, Any, List
import struct
from .base import BaseChunk, ChunkParsingError

class MmidChunk(BaseChunk):
    """MMID (M2 Model Offset) chunk parser.
    
    Contains offsets into the MMDX chunk for model filenames.
    Each entry is a uint32 offset.
    """
    
    def parse(self) -> Dict[str, Any]:
        """Parse MMID chunk data."""
        if len(self.data) % 4 != 0:
            raise ChunkParsingError(f"MMID chunk size {len(self.data)} not divisible by 4")
        
        count = len(self.data) // 4
        offsets = struct.unpack(f'<{count}I', self.data)
        
        return {
            'offsets': list(offsets),
            'count': count
        }
