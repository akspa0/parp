# adt_analyzer/chunks/mhdr/parser.py
from typing import Dict, Any
import struct
import logging
from ..base import BaseChunk, ChunkParsingError
from .flags import MhdrFlags

logger = logging.getLogger(__name__)

class MhdrChunk(BaseChunk):
    """MHDR (ADT Header) parser.
    
    Contains flags and offsets to other chunks in the file.
    Always 64 bytes in size.
    """
    
    EXPECTED_SIZE = 64
    
    def parse(self) -> Dict[str, Any]:
        """Parse MHDR chunk data."""
        if len(self.data) != self.EXPECTED_SIZE:
            raise ChunkParsingError(
                f"MHDR chunk size {len(self.data)} != {self.EXPECTED_SIZE}"
            )
        
        try:
            # Unpack all values (16 uint32 values)
            values = struct.unpack('<16I', self.data)
            
            flags = MhdrFlags(values[0])
            
            return {
                'flags': {
                    'raw_value': values[0],
                    'has_mfbo': bool(flags & MhdrFlags.HAS_MFBO),
                    'has_mh2o': bool(flags & MhdrFlags.HAS_MH2O),
                    'has_mtxf': bool(flags & MhdrFlags.HAS_MTXF),
                    'use_big_alpha': bool(flags & MhdrFlags.USE_BIG_ALPHA),
                    'use_big_textures': bool(flags & MhdrFlags.USE_BIG_TEXTURES),
                    'use_mcsh': bool(flags & MhdrFlags.USE_MCSH)
                },
                'offsets': {
                    'mcin': values[1],  # Chunk index
                    'mtex': values[2],  # Textures
                    'mmdx': values[3],  # M2 models
                    'mmid': values[4],  # Model indices
                    'mwmo': values[5],  # WMO models
                    'mwid': values[6],  # WMO indices
                    'mddf': values[7],  # Doodad placement
                    'modf': values[8],  # WMO placement
                    'mfbo': values[9],  # Flight bounds
                    'mh2o': values[10], # Water data
                    'mtxf': values[11], # Texture flags
                    'unused': values[12:] # Last 4 values are unused
                }
            }
            
        except struct.error as e:
            raise ChunkParsingError(f"Failed to parse MHDR data: {e}")
