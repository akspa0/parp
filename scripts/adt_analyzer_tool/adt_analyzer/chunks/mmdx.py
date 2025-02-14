# adt_analyzer/chunks/mmdx.py
from typing import Dict, Any, List
from .base import BaseChunk

class MmdxChunk(BaseChunk):
    """MMDX (M2 Model Filename) chunk parser.
    
    Contains a list of null-terminated M2 model filenames.
    Used in conjunction with MMID chunk which provides offsets.
    """
    
    def parse(self) -> Dict[str, Any]:
        """Parse MMDX chunk data.
        Returns raw block for processing with MMID offsets."""
        return {
            'model_name_block': self.data,
            'size': len(self.data)
        }