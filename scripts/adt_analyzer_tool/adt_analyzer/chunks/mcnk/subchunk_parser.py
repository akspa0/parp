# adt_analyzer/chunks/mcnk/subchunk_parser.py
from typing import Dict, Any, Optional, Type
import logging
from ..base import BaseChunk

logger = logging.getLogger(__name__)

class SubchunkParser:
    """Handles parsing of MCNK sub-chunks."""
    
    def __init__(self, chunk_data: bytes):
        self.data = chunk_data

    def parse_subchunk(self, 
                      chunk_class: Type[BaseChunk], 
                      offset: int, 
                      size: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Parse a sub-chunk from the data."""
        if offset == 0:
            return None

        try:
            chunk_data = self.data[offset:]
            if size:
                chunk_data = chunk_data[:size]

            chunk = chunk_class(
                header=chunk_class.from_bytes(chunk_data).header,
                data=chunk_data
            )
            return chunk.parse()
        except Exception as e:
            logger.error(f"Failed to parse {chunk_class.__name__} at offset {offset}: {e}")
            return None

    def parse_texture_layers(self, mcly_offset: int, mcal_offset: int, 
                           mcal_size: int) -> Dict[str, Any]:
        """Parse texture layers and their alpha maps."""
        from ..mcly import MclyChunk
        from ..mcal import McalChunk
        
        result = {}
        
        # Parse MCLY first
        if mcly_data := self.parse_subchunk(MclyChunk, mcly_offset):
            result['mcly'] = mcly_data
            
            # Then parse MCAL using MCLY information
            if mcal_offset and mcal_size:
                if mcal_data := self.parse_subchunk(McalChunk, mcal_offset, mcal_size):
                    result['mcal'] = mcal_data
        
        return result
