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

    def parse_structured(self) -> Dict[str, Any]:
        """Parse MWID chunk data into structured format.
        
        Returns:
            Dictionary containing:
            - offsets: List of dicts with index and offset
            - count: Number of offsets
        """
        if len(self.data) % 4 != 0:
            raise ChunkParsingError(
                f"MWID chunk size {len(self.data)} not divisible by 4"
            )
        
        count = len(self.data) // 4
        structured_offsets = []
        
        for i in range(count):
            offset = struct.unpack('<I', self.data[i*4:(i+1)*4])[0]
            structured_offsets.append({
                'index': i,
                'offset': offset
            })
        
        return {
            'offsets': structured_offsets,
            'count': count
        }
