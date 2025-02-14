# adt_analyzer/chunks/mhdr.py
from typing import Dict, Any
import struct
from .base import BaseChunk, ChunkParsingError

class MhdrChunk(BaseChunk):
    """MHDR (Header) chunk parser.
    
    Contains offsets to other chunks in the file.
    Size is always 64 bytes.
    """
    
    EXPECTED_SIZE = 64
    
    def parse(self) -> Dict[str, Any]:
        """Parse MHDR chunk data."""
        if len(self.data) != self.EXPECTED_SIZE:
            raise ChunkParsingError(f"MHDR chunk size {len(self.data)} != {self.EXPECTED_SIZE}")
        
        # Unpack all offsets
        offsets = struct.unpack('<16I', self.data)
        
        return {
            'flags': offsets[0],
            'mcin_offset': offsets[1],  # Offset to MCIN chunk
            'mtex_offset': offsets[2],  # Offset to MTEX chunk
            'mmdx_offset': offsets[3],  # Offset to MMDX chunk
            'mmid_offset': offsets[4],  # Offset to MMID chunk
            'mwmo_offset': offsets[5],  # Offset to MWMO chunk
            'mwid_offset': offsets[6],  # Offset to MWID chunk
            'mddf_offset': offsets[7],  # Offset to MDDF chunk
            'modf_offset': offsets[8],  # Offset to MODF chunk
            'mfbo_offset': offsets[9],  # Offset to MFBO chunk
            'mh2o_offset': offsets[10], # Offset to MH2O chunk
            'mtxf_offset': offsets[11], # Offset to MTXF chunk
            'padding': offsets[12:],    # Unused padding
        }
