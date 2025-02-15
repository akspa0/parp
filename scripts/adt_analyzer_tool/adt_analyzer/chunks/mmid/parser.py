"""MMID (M2 Model Indices) chunk parser."""
from typing import Dict, Any, List
import struct
from ..base import BaseChunk, ChunkParsingError

class MmidChunk(BaseChunk):
    """MMID chunk parser.
    
    Contains offsets into the MMDX chunk for model filenames.
    Each entry is a uint32 offset.
    """
    
    def parse(self) -> Dict[str, Any]:
        """Parse MMID chunk data.
        
        Returns:
            Dictionary containing:
            - offsets: List of uint32 offsets into MMDX chunk
            - count: Number of offsets
        """
        if len(self.data) % 4 != 0:
            raise ChunkParsingError(
                f"MMID chunk size {len(self.data)} not divisible by 4"
            )
        
        count = len(self.data) // 4
        offsets = list(struct.unpack(f'<{count}I', self.data))
        
        return {
            'offsets': offsets,
            'count': count
        }
