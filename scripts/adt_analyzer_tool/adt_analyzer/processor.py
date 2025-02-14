# adt_analyzer/processor.py
from typing import Dict, Any, Optional, Type, List
import logging
import struct
from pathlib import Path

from .chunks.base import BaseChunk, ChunkParsingError
from .chunks.mcin.parser import McinChunk
from .chunks.mcnk.parser import McnkChunk
# Import other chunk parsers as they're implemented

logger = logging.getLogger(__name__)

class ChunkRegistry:
    """Registry of chunk parsers mapped to chunk names."""
    
    def __init__(self):
        self._parsers: Dict[bytes, Type[BaseChunk]] = {}
        self._reverse_parsers: Dict[bytes, Type[BaseChunk]] = {}
    
    def register(self, chunk_name: bytes, parser_class: Type[BaseChunk]) -> None:
        """Register a parser for a chunk type."""
        self._parsers[chunk_name] = parser_class
        # Also register reversed name for handling both orientations
        self._reverse_parsers[chunk_name[::-1]] = parser_class
    
    def get_parser(self, chunk_name: bytes) -> Optional[Type[BaseChunk]]:
        """Get parser for chunk name, trying both orientations."""
        return self._parsers.get(chunk_name) or self._reverse_parsers.get(chunk_name)

class AdtProcessor:
    """Main ADT file processor.
    
    Handles reading ADT files and coordinating chunk parsing.
    """
    
    def __init__(self):
        self.chunk_registry = ChunkRegistry()
        self._register_chunk_parsers()
    
    def _register_chunk_parsers(self) -> None:
        """Register all available chunk parsers."""
        # Register parsers as they're implemented
        self.chunk_registry.register(b'MCIN', McinChunk)
        self.chunk_registry.register(b'MCNK', McnkChunk)
        # Add more registrations as we implement them
    
    def _read_chunk_header(self, data: bytes, offset: int) -> Optional[Dict[str, Any]]:
        """Read a chunk header from the given offset."""
        try:
            if offset + 8 > len(data):
                return None
            
            chunk_name = data[offset:offset+4]
            chunk_size = struct.unpack('<I', data[offset+4:offset+8])[0]
            
            return {
                'name': chunk_name,
                'size': chunk_size,
                'offset': offset
            }
        except Exception as e:
            logger.error(f"Failed to read chunk header at offset {offset}: {e}")
            return None
    
    def process_file(self, file_path: Path) -> Dict[str, Any]:
        """Process an ADT file and return structured data."""
        logger.info(f"Processing ADT file: {file_path}")
        result = {
            'file_path': str(file_path),
            'chunks': {},
            'errors': []
        }
        
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            offset = 0
            while offset < len(data):
                # Read chunk header
                chunk_header = self._read_chunk_header(data, offset)
                if not chunk_header:
                    break
                
                chunk_name = chunk_header['name']
                chunk_size = chunk_header['size']
                
                # Find parser for this chunk type
                parser_class = self.chunk_registry.get_parser(chunk_name)
                
                if parser_class:
                    try:
                        # Extract chunk data
                        chunk_data = data[offset+8:offset+8+chunk_size]
                        
                        # Parse chunk
                        chunk = parser_class(
                            header=parser_class.from_bytes(chunk_data).header,
                            data=chunk_data
                        )
                        parsed_data = chunk.parse()
                        
                        # Store result
                        result['chunks'][chunk_name.decode('ascii')] = {
                            'offset': offset,
                            'size': chunk_size,
                            'data': parsed_data
                        }
                        
                    except Exception as e:
                        error_msg = f"Failed to parse {chunk_name} chunk: {e}"
                        logger.error(error_msg)
                        result['errors'].append(error_msg)
                else:
                    # Log unhandled chunk type
                    logger.debug(f"No parser registered for chunk type: {chunk_name}")
                
                # Move to next chunk
                offset += 8 + chunk_size
        
        except Exception as e:
            error_msg = f"Failed to process file {file_path}: {e}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
        
        return result
