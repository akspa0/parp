# adt_analyzer/chunks/mcsh.py
from typing import Dict, Any
from .base import BaseChunk

class McshChunk(BaseChunk):
    """MCSH (Shadow Map) chunk parser.
    
    Contains shadow map information.
    64x64 bytes, one byte per cell.
    """
    
    EXPECTED_SIZE = 64 * 64
    
    def parse(self) -> Dict[str, Any]:
        """Parse MCSH chunk data."""
        if len(self.data) != self.EXPECTED_SIZE:
            return {
                'shadow_map': list(self.data),
                'complete': False
            }
            
        return {
            'shadow_map': list(self.data),
            'complete': True
        }
