# adt_analyzer/chunks/mtex/parser.py
from typing import Dict, Any, List
import logging
from ..base import BaseChunk

logger = logging.getLogger(__name__)

class MtexChunk(BaseChunk):
    """MTEX (Texture Names) parser.
    
    Contains a list of null-terminated strings for texture filenames.
    Variable size chunk.
    """
    
    def _parse_texture_list(self, data: bytes) -> List[str]:
        """Parse null-terminated texture filenames."""
        textures = []
        current_texture = bytearray()
        
        for byte in data:
            if byte == 0:  # Null terminator
                if current_texture:
                    try:
                        texture_name = current_texture.decode('utf-8')
                        textures.append(texture_name)
                        current_texture = bytearray()
                    except UnicodeDecodeError as e:
                        logger.warning(f"Failed to decode texture name: {e}")
                        current_texture = bytearray()
            else:
                current_texture.append(byte)
        
        # Handle last texture if data doesn't end with null
        if current_texture:
            try:
                texture_name = current_texture.decode('utf-8')
                textures.append(texture_name)
            except UnicodeDecodeError as e:
                logger.warning(f"Failed to decode final texture name: {e}")
        
        return textures
    
    def parse(self) -> Dict[str, Any]:
        """Parse MTEX chunk data."""
        try:
            textures = self._parse_texture_list(self.data)
            
            # Basic validation
            for texture in textures:
                if not texture.lower().endswith(('.blp', '.dds')):
                    logger.warning(f"Unusual texture extension: {texture}")
            
            return {
                'textures': textures,
                'count': len(textures)
            }
            
        except Exception as e:
            raise ChunkParsingError(f"Failed to parse MTEX data: {e}")

# Example usage:
if __name__ == "__main__":
    # Simple test data
    test_mtex_data = b'ground1.blp\0ground2.blp\0cliff1.blp\0'
    chunk = MtexChunk(header=None, data=test_mtex_data)
    result = chunk.parse()
    print(f"Found {result['count']} textures:")
    for texture in result['textures']:
        print(f"  {texture}")
