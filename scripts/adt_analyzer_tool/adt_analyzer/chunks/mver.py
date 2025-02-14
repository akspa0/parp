# adt_analyzer/chunks/mver.py
from typing import Dict, Any
import struct
from .base import BaseChunk, ChunkParsingError

class MverChunk(BaseChunk):
    """MVER (Version) chunk parser."""
    
    EXPECTED_SIZE = 4
    
    def parse(self) -> Dict[str, Any]:
        """Parse MVER chunk data.
        Returns version number of the ADT file."""
        if len(self.data) != self.EXPECTED_SIZE:
            raise ChunkParsingError(f"MVER chunk size {len(self.data)} != {self.EXPECTED_SIZE}")
        
        version = struct.unpack('<I', self.data)[0]
        return {
            'version': version
        }
