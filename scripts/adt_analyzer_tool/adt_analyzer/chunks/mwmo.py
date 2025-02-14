# adt_analyzer/chunks/mwmo.py
from typing import Dict, Any
from .base import BaseChunk

class MwmoChunk(BaseChunk):
    """MWMO (WMO Filename) chunk parser.
    
    Contains a list of null-terminated WMO model filenames.
    Used in conjunction with MWID chunk which provides offsets.
    """
    
    def parse(self) -> Dict[str, Any]:
        """Parse MWMO chunk data.
        Returns raw block for processing with MWID offsets."""
        return {
            'wmo_name_block': self.data,
            'size': len(self.data)
        }