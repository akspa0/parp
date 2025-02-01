"""
Base class for chunk-based file parsing.
Provides memory-mapped file access and chunk iteration functionality.
"""
from typing import Dict, Any, Iterator, Tuple, Optional, BinaryIO, List
from dataclasses import dataclass
from pathlib import Path
import mmap
import struct
import logging
from abc import ABC, abstractmethod

@dataclass
class ChunkHeader:
    """Chunk header information"""
    name: str
    size: int
    offset: int
    data_offset: int

class ChunkParser(ABC):
    """Base class for chunk-based parsing"""
    
    KNOWN_CHUNKS = [b'MVER', b'MPHD', b'MAIN', b'MDNM', b'MONM', b'MCNK']
    
    def __init__(self):
        """Initialize the chunk parser"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.mm: Optional[mmap.mmap] = None
        self.file: Optional[BinaryIO] = None
        self.file_path: Optional[Path] = None
        self.chunk_registry: Dict[str, Any] = {}
        self.reverse_names = False  # Some formats need name bytes reversed
        self.chunk_index: Dict[str, List[ChunkHeader]] = {}
        
        # Setup chunk parsers
        self._setup_chunk_registry()
    
    @abstractmethod
    def _setup_chunk_registry(self) -> None:
        """
        Register chunk parsers
        Must be implemented by format-specific classes
        """
        pass
    
    def _detect_name_reversal(self):
        """
        Detect if chunk names need to be reversed
        This is crucial for handling different WoW file formats
        """
        pos = 0
        while pos + 8 <= len(self.mm):
            magic = self.mm[pos:pos+4]
            if magic in self.KNOWN_CHUNKS:
                self.reverse_names = False
                return
            if magic[::-1] in self.KNOWN_CHUNKS:
                self.reverse_names = True
                return
            size = struct.unpack('<I', self.mm[pos+4:pos+8])[0]
            pos += 8 + size
        
        self.logger.warning("Could not definitively detect chunk name orientation")
        self.reverse_names = False
    
    def _build_chunk_index(self):
        """
        Build an index of all chunks in the file
        This allows for faster access to specific chunk types
        """
        self.chunk_index.clear()
        pos = 0
        
        while pos < len(self.mm):
            if pos + 8 > len(self.mm):
                break
            
            try:
                magic_raw = self.mm[pos:pos+4]
                magic = magic_raw[::-1] if self.reverse_names else magic_raw
                magic_str = magic.decode('ascii')
                size = struct.unpack('<I', self.mm[pos+4:pos+8])[0]
                
                header = ChunkHeader(
                    name=magic_str,
                    size=size,
                    offset=pos,
                    data_offset=pos + 8
                )
                
                if magic_str not in self.chunk_index:
                    self.chunk_index[magic_str] = []
                self.chunk_index[magic_str].append(header)
                
                pos += 8 + size
                
            except Exception as e:
                self.logger.error(f"Error indexing chunk at offset {pos}: {e}")
                break
    
    def open(self, file_path: str | Path) -> None:
        """
        Open file for parsing using memory mapping
        
        Args:
            file_path: Path to file to parse
            
        Raises:
            FileNotFoundError: If file does not exist
            IOError: If file cannot be opened
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")
        
        try:
            self.file = open(self.file_path, 'rb')
            self.mm = mmap.mmap(self.file.fileno(), 0, access=mmap.ACCESS_READ)
            self._detect_name_reversal()
            self._build_chunk_index()
        except Exception as e:
            self.logger.error(f"Failed to open file: {e}")
            if self.file:
                self.file.close()
            raise
    
    def close(self) -> None:
        """Close file and cleanup memory mapping"""
        if self.mm:
            self.mm.close()
            self.mm = None
        if self.file:
            self.file.close()
            self.file = None
        self.chunk_index.clear()
    
    def get_data_at_offset(self, offset: int, size: int) -> bytes:
        """
        Get data at specified offset
        
        Args:
            offset: Offset in file
            size: Number of bytes to read
            
        Returns:
            Bytes at specified offset
            
        Raises:
            RuntimeError: If no file is opened
            ValueError: If offset or size is invalid
        """
        if not self.mm:
            raise RuntimeError("No file opened")
        
        if offset < 0 or offset + size > len(self.mm):
            raise ValueError(f"Invalid offset ({offset}) or size ({size})")
        
        return self.mm[offset:offset + size]
    
    def get_chunks_by_type(self, chunk_type: str) -> Iterator[Tuple[ChunkHeader, bytes]]:
        """
        Get all chunks of a specific type
        
        Args:
            chunk_type: Type of chunks to find
            
        Yields:
            Tuple of (ChunkHeader, chunk_data)
        """
        for header in self.chunk_index.get(chunk_type, []):
            chunk_data = self.get_data_at_offset(header.data_offset, header.size)
            yield header, chunk_data
    
    def iterate_chunks(self, data: Optional[bytes] = None) -> Iterator[Tuple[ChunkHeader, bytes]]:
        """
        Iterate over chunks in file or raw data
        
        Args:
            data: Optional raw data to parse. If None, uses memory-mapped file.
            
        Yields:
            Tuple of (ChunkHeader, chunk_data)
            
        Raises:
            RuntimeError: If no file is opened and no data provided
        """
        if data is None:
            if not self.mm:
                raise RuntimeError("No file opened and no data provided")
            
            # Use indexed chunks if available
            for chunk_list in self.chunk_index.values():
                for header in chunk_list:
                    chunk_data = self.get_data_at_offset(header.data_offset, header.size)
                    yield header, chunk_data
            return
        
        # Parse raw data
        pos = 0
        while pos < len(data):
            if pos + 8 > len(data):
                break
            
            # Parse chunk header
            chunk_name_raw = data[pos:pos+4]
            chunk_name = chunk_name_raw[::-1].decode('ascii', 'ignore') if self.reverse_names else chunk_name_raw.decode('ascii', 'ignore')
            chunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]
            
            # Create header
            header = ChunkHeader(
                name=chunk_name,
                size=chunk_size,
                offset=pos,
                data_offset=pos + 8
            )
            
            # Get chunk data
            if pos + 8 + chunk_size > len(data):
                self.logger.warning(f"Chunk {chunk_name} extends beyond data bounds")
                break
            
            chunk_data = data[pos+8:pos+8+chunk_size]
            yield header, chunk_data
            
            pos += 8 + chunk_size
    
    def parse_chunk(self, header: ChunkHeader, data: bytes) -> Dict[str, Any]:
        """
        Parse a chunk using registered parser
        
        Args:
            header: Chunk header
            data: Chunk data
            
        Returns:
            Dictionary containing parsed chunk data
            
        Raises:
            ValueError: If no parser registered for chunk type
        """
        parser = self.chunk_registry.get(header.name)
        if not parser:
            raise ValueError(f"No parser registered for chunk type: {header.name}")
        
        try:
            return parser(data)
        except Exception as e:
            self.logger.error(f"Error parsing {header.name} chunk: {e}")
            raise
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()