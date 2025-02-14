# adt_analyzer/chunks/mtex.py
from typing import Dict, Any, List
from .base import BaseChunk

class MtexChunk(BaseChunk):
    """MTEX (Texture) chunk parser.
    
    Contains a list of null-terminated texture filenames.
    """
    
    def parse(self) -> Dict[str, Any]:
        """Parse MTEX chunk data."""
        # Split on null bytes and decode each string
        texture_list = self.data.split(b'\0')
        textures = [tex.decode('utf-8', 'replace') for tex in texture_list if tex]
        
        return {
            'textures': textures,
            'count': len(textures)
        }
