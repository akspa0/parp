# adt_analyzer/chunks/mmdx/parser.py
from typing import Dict, Any, List
import logging
from ..base import BaseChunk, ChunkParsingError

logger = logging.getLogger(__name__)

class MmdxChunk(BaseChunk):
    """MMDX (Model Definitions) parser.
    
    Contains a series of null-terminated strings for M2 model filenames.
    Used in conjunction with MMID chunk which provides offsets into this data.
    """
    
    def _extract_model_names(self, data: bytes) -> List[Dict[str, Any]]:
        """Extract model names and their positions in the data block."""
        models = []
        current_offset = 0
        current_name = bytearray()
        
        for byte in data:
            if byte == 0:  # Null terminator
                if current_name:
                    try:
                        name = current_name.decode('utf-8')
                        models.append({
                            'name': name,
                            'offset': current_offset,
                            'length': len(current_name)
                        })
                        current_name = bytearray()
                    except UnicodeDecodeError as e:
                        logger.warning(
                            f"Failed to decode model name at offset {current_offset}: {e}"
                        )
                        current_name = bytearray()
                current_offset += 1  # Include null terminator
            else:
                current_name.append(byte)
                current_offset += 1
        
        # Handle any remaining data
        if current_name:
            try:
                name = current_name.decode('utf-8')
                models.append({
                    'name': name,
                    'offset': current_offset - len(current_name),
                    'length': len(current_name)
                })
            except UnicodeDecodeError as e:
                logger.warning(f"Failed to decode final model name: {e}")
        
        return models
    
    def parse(self) -> Dict[str, Any]:
        """Parse MMDX chunk data."""
        try:
            models = self._extract_model_names(self.data)
            
            # Basic validation
            for model in models:
                name = model['name']
                if not name.lower().endswith(('.m2', '.mdx')):
                    logger.warning(f"Unusual model extension: {name}")
                if model['offset'] + model['length'] > len(self.data):
                    logger.error(f"Model entry extends beyond chunk data: {name}")
            
            return {
                'models': models,
                'count': len(models),
                'data_size': len(self.data)
            }
            
        except Exception as e:
            raise ChunkParsingError(f"Failed to parse MMDX data: {e}")