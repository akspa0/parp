"""MMDX (M2 Model Filenames) chunk parser."""
from typing import Dict, Any
import struct
from ..base import BaseChunk, ChunkParsingError

class MmdxChunk(BaseChunk):
    """MMDX chunk parser.
    
    Contains a list of M2 model filenames used in the ADT file.
    Each filename is null-terminated.
    """
    
    def parse(self) -> Dict[str, Any]:
        """Parse MMDX chunk data.
        
        Returns:
            Dictionary containing:
            - model_name_block: Raw data block containing null-terminated filenames
            - size: Size of the data block
        """
        return {
            'model_name_block': self.data,
            'size': len(self.data)
        }

    def parse_filenames(self) -> Dict[str, Any]:
        """Parse MMDX chunk data into structured format.
        
        Returns:
            Dictionary containing:
            - models: List of model entries with name, offset, and length
            - count: Number of models
            - data_size: Total size of model name data
        """
        models = []
        offset = 0
        
        while offset < len(self.data):
            # Find end of current string
            end = self.data.find(b'\0', offset)
            if end == -1:
                break
                
            # Extract and decode filename
            name = self.data[offset:end].decode('utf-8')
            length = end - offset + 1  # Include null terminator
            
            models.append({
                'name': name,
                'offset': offset,
                'length': length
            })
            
            offset = end + 1
        
        return {
            'models': models,
            'count': len(models),
            'data_size': offset
        }