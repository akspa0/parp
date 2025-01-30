"""
Abstract base class for chunk parsing.
Provides common functionality for parsing WDT/ADT chunks.
"""
from abc import ABC, abstractmethod
import struct
import mmap
from dataclasses import dataclass
from typing import Dict, Any, Generator, Tuple, Optional
import logging
from pathlib import Path

@dataclass
class ChunkHeader:
    """Represents a chunk header with name and size"""
    name: str
    size: int
    offset: int  # Offset to chunk start (including header)
    data_offset: int  # Offset to chunk data (after header)

class ChunkParser(ABC):
    """Abstract base class for chunk parsing"""
    
    def __init__(self):
        """Initialize the chunk parser"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.mm: Optional[mmap.mmap] = None
        self.chunk_registry: Dict[str, Any] = {}  # Maps chunk names to parser functions
        self._setup_chunk_registry()
    
    @abstractmethod
    def _setup_chunk_registry(self) -> None:
        """
        Setup the chunk registry with parser functions.
        Must be implemented by derived classes to register chunk-specific parsers.
        """
        pass
    
    def open(self, file_path: str | Path) -> None:
        """
        Open and memory map the file for parsing
        
        Args:
            file_path: Path to the file to parse
            
        Raises:
            FileNotFoundError: If file does not exist
            IOError: If file cannot be opened/mapped
        """
        try:
            self.file = open(file_path, 'rb')
            self.mm = mmap.mmap(self.file.fileno(), 0, access=mmap.ACCESS_READ)
        except Exception as e:
            if hasattr(self, 'file'):
                self.file.close()
            raise IOError(f"Failed to open/map file {file_path}: {e}")
    
    def close(self) -> None:
        """Close the memory mapped file"""
        if self.mm:
            self.mm.close()
            self.mm = None
        if hasattr(self, 'file'):
            self.file.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
    
    def read_chunk_header(self, offset: int) -> ChunkHeader:
        """
        Read a chunk header at the given offset
        
        Args:
            offset: Offset in file to read header from
            
        Returns:
            ChunkHeader containing chunk name and size
            
        Raises:
            ValueError: If header cannot be read
        """
        if not self.mm:
            raise ValueError("No file opened")
            
        if offset + 8 > len(self.mm):
            raise ValueError(f"Invalid offset {offset} - beyond file end")
            
        try:
            # Read and decode chunk name (4 bytes)
            chunk_name = self.mm[offset:offset+4]
            chunk_name = chunk_name[::-1].decode('ascii', 'ignore')  # Reverse bytes for correct order
            
            # Read chunk size (4 bytes)
            chunk_size = struct.unpack('<I', self.mm[offset+4:offset+8])[0]
            
            return ChunkHeader(
                name=chunk_name,
                size=chunk_size,
                offset=offset,
                data_offset=offset + 8
            )
        except Exception as e:
            raise ValueError(f"Failed to read chunk header at offset {offset}: {e}")
    
    def iterate_chunks(self) -> Generator[Tuple[ChunkHeader, bytes], None, None]:
        """
        Iterate through all chunks in the file
        
        Yields:
            Tuple of (ChunkHeader, chunk_data)
        """
        if not self.mm:
            raise ValueError("No file opened")
            
        pos = 0
        while pos < len(self.mm):
            try:
                header = self.read_chunk_header(pos)
                data = self.mm[header.data_offset:header.data_offset + header.size]
                yield header, data
                pos = header.data_offset + header.size
            except ValueError as e:
                self.logger.error(f"Error reading chunk at offset {pos}: {e}")
                break
    
    def get_chunks_by_name(self, chunk_name: str) -> Generator[Tuple[ChunkHeader, bytes], None, None]:
        """
        Get all chunks with the specified name
        
        Args:
            chunk_name: Name of chunks to find (e.g., 'MVER', 'MAIN')
            
        Yields:
            Tuple of (ChunkHeader, chunk_data) for each matching chunk
        """
        for header, data in self.iterate_chunks():
            if header.name == chunk_name:
                yield header, data
    
    def parse_chunk(self, header: ChunkHeader, data: bytes) -> Dict[str, Any]:
        """
        Parse a chunk using the registered parser function
        
        Args:
            header: Chunk header
            data: Raw chunk data
            
        Returns:
            Dictionary containing parsed chunk data
            
        Raises:
            ValueError: If no parser is registered for the chunk type
        """
        parser = self.chunk_registry.get(header.name)
        if not parser:
            raise ValueError(f"No parser registered for chunk type {header.name}")
            
        try:
            return parser(data)
        except Exception as e:
            self.logger.error(f"Error parsing {header.name} chunk: {e}")
            return {'error': str(e)}
    
    @abstractmethod
    def parse(self) -> Dict[str, Any]:
        """
        Parse the entire file
        Must be implemented by derived classes to define file-specific parsing logic
        
        Returns:
            Dictionary containing all parsed data
        """
        pass