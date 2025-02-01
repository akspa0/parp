"""
Base parser class for chunk-based file formats.
Provides common functionality for reading binary data and handling chunks.
"""
import struct
import logging
from typing import BinaryIO, Generator, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ChunkInfo:
    """Information about a chunk's location in a file"""
    magic: bytes
    offset: int
    size: int
    data_offset: int

class ParsingError(Exception):
    """Base class for parsing errors"""
    pass

class ChunkError(ParsingError):
    """Error related to chunk parsing"""
    pass

class BinaryParser:
    """Base class for binary file parsing"""
    
    def __init__(self, file_path: str, reversed_chunks: bool = False):
        """
        Initialize the parser
        
        Args:
            file_path: Path to the file to parse
            reversed_chunks: Whether chunk magic values are reversed
        """
        self.file_path = Path(file_path)
        self.reversed_chunks = reversed_chunks
        self._file: Optional[BinaryIO] = None
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def __enter__(self):
        """Context manager entry"""
        self.open()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        
    def open(self):
        """Open the file for reading"""
        if self._file is None:
            try:
                self._file = open(self.file_path, 'rb')
            except OSError as e:
                raise ParsingError(f"Failed to open {self.file_path}: {e}")
                
    def close(self):
        """Close the file if open"""
        if self._file is not None:
            self._file.close()
            self._file = None
            
    def read_bytes(self, size: int) -> bytes:
        """Read exact number of bytes"""
        if self._file is None:
            raise ParsingError("File not open")
            
        data = self._file.read(size)
        if len(data) != size:
            raise ParsingError(f"Failed to read {size} bytes")
        return data
        
    def read_struct(self, fmt: str) -> tuple:
        """Read and unpack binary structure"""
        size = struct.calcsize(fmt)
        data = self.read_bytes(size)
        try:
            return struct.unpack(fmt, data)
        except struct.error as e:
            raise ParsingError(f"Failed to unpack struct: {e}")
            
    def read_cstring(self) -> str:
        """Read null-terminated string"""
        chars = []
        while True:
            char = self.read_bytes(1)
            if char == b'\0':
                break
            chars.append(char)
        return b''.join(chars).decode('utf-8', errors='replace')
        
    def read_chunk_header(self) -> Tuple[bytes, int]:
        """Read chunk header (magic + size)"""
        try:
            magic = self.read_bytes(4)
            if self.reversed_chunks:
                magic = magic[::-1]
            size = self.read_struct('<I')[0]
            return magic, size
        except ParsingError as e:
            raise ChunkError(f"Failed to read chunk header: {e}")
            
    def read_chunk(self, chunk: ChunkInfo) -> bytes:
        """Read chunk data"""
        if self._file is None:
            raise ParsingError("File not open")
            
        self._file.seek(chunk.data_offset)
        return self.read_bytes(chunk.size)
        
    def find_chunks(self, magic: Optional[bytes] = None) -> Generator[ChunkInfo, None, None]:
        """
        Find all chunks or chunks matching specific magic
        
        Args:
            magic: Optional 4-byte chunk identifier to match
            
        Yields:
            ChunkInfo for each matching chunk
        """
        if self._file is None:
            raise ParsingError("File not open")
            
        self._file.seek(0)
        while True:
            chunk_start = self._file.tell()
            
            # Try to read chunk header
            try:
                chunk_magic, chunk_size = self.read_chunk_header()
            except (ParsingError, ChunkError):
                break
                
            # Create chunk info
            chunk = ChunkInfo(
                magic=chunk_magic,
                offset=chunk_start,
                size=chunk_size,
                data_offset=chunk_start + 8
            )
            
            # Check if chunk matches requested magic
            if magic is None or chunk.magic == magic:
                yield chunk
                
            # Skip to next chunk
            try:
                self._file.seek(chunk.data_offset + chunk.size)
            except OSError:
                break
                
    def validate_file(self) -> bool:
        """
        Validate basic file structure
        
        Returns:
            bool: Whether file appears valid
        """
        try:
            self.open()
            # Try to read first chunk header
            self._file.seek(0)
            self.read_chunk_header()
            return True
        except (ParsingError, ChunkError):
            return False
        finally:
            self.close()