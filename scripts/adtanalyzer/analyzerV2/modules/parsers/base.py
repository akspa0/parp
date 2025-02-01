"""
Base parser for WoW terrain files.
Provides common functionality for ADT and WDT parsers.
"""
import struct
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union

from ..models import TerrainFile
from ..utils import get_logger

class ParserError(Exception):
    """Base class for parser errors"""
    pass

class ChunkError(ParserError):
    """Error parsing a specific chunk"""
    pass

class BaseParser(ABC):
    """Base class for terrain file parsers"""
    
    def __init__(self, file_path: Union[str, Path]):
        """
        Initialize parser
        
        Args:
            file_path: Path to terrain file
        """
        self.path = Path(file_path)
        self.logger = get_logger(f"{self.__class__.__name__}")
        self._file: Optional[BinaryIO] = None
        self._chunk_order: List[str] = []
        
    def __enter__(self):
        """Context manager entry"""
        self.open()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        
    def open(self) -> None:
        """Open file for reading"""
        if self._file is None:
            self._file = open(self.path, 'rb')
            
    def close(self) -> None:
        """Close file if open"""
        if self._file is not None:
            self._file.close()
            self._file = None
            
    def read_bytes(self, size: int) -> bytes:
        """
        Read bytes from file
        
        Args:
            size: Number of bytes to read
            
        Returns:
            Bytes read
            
        Raises:
            EOFError: If not enough bytes available
        """
        if self._file is None:
            raise RuntimeError("File not open")
            
        data = self._file.read(size)
        if len(data) < size:
            raise EOFError(f"Expected {size} bytes, got {len(data)}")
            
        return data
        
    def read_struct(self, fmt: str) -> Tuple:
        """
        Read and unpack binary structure
        
        Args:
            fmt: Struct format string
            
        Returns:
            Unpacked values
        """
        size = struct.calcsize(fmt)
        data = self.read_bytes(size)
        return struct.unpack(fmt, data)
        
    def read_string(self, size: Optional[int] = None, encoding: str = 'utf-8') -> str:
        """
        Read null-terminated or fixed-size string
        
        Args:
            size: Fixed size to read, or None for null-terminated
            encoding: String encoding
            
        Returns:
            Decoded string
        """
        if size is not None:
            data = self.read_bytes(size)
        else:
            chars = []
            while True:
                char = self.read_bytes(1)[0]
                if char == 0:
                    break
                chars.append(char)
            data = bytes(chars)
            
        return data.decode(encoding).rstrip('\0')
        
    def seek(self, offset: int, whence: int = 0) -> None:
        """
        Seek to position in file
        
        Args:
            offset: Byte offset
            whence: Seek reference point (0=start, 1=current, 2=end)
        """
        if self._file is None:
            raise RuntimeError("File not open")
            
        self._file.seek(offset, whence)
        
    def tell(self) -> int:
        """
        Get current file position
        
        Returns:
            Current byte offset
        """
        if self._file is None:
            raise RuntimeError("File not open")
            
        return self._file.tell()
        
    @abstractmethod
    def parse(self) -> TerrainFile:
        """
        Parse terrain file
        
        Returns:
            Parsed terrain file data
            
        Raises:
            ParserError: On parsing errors
        """
        pass
        
    @abstractmethod
    def parse_chunk(self, chunk_name: str, size: int) -> Any:
        """
        Parse a specific chunk
        
        Args:
            chunk_name: Four character chunk name
            size: Chunk data size in bytes
            
        Returns:
            Parsed chunk data
            
        Raises:
            ChunkError: On chunk parsing errors
        """
        pass
        
    def read_chunk_header(self) -> Tuple[str, int]:
        """
        Read chunk header
        
        Returns:
            Tuple of (chunk_name, data_size)
        """
        name = self.read_string(4)
        size = self.read_struct('<I')[0]
        self._chunk_order.append(name)
        return name, size
        
    def skip_chunk(self, size: int) -> None:
        """
        Skip chunk data
        
        Args:
            size: Number of bytes to skip
        """
        self.seek(size, 1)  # Seek relative to current position
        
    def parse_chunks(self) -> Dict[str, Any]:
        """
        Parse all chunks in file
        
        Returns:
            Dictionary of chunk data keyed by chunk name
        """
        chunks = {}
        
        try:
            while True:
                chunk_start = self.tell()
                try:
                    name, size = self.read_chunk_header()
                except EOFError:
                    break  # End of file reached
                    
                try:
                    chunks[name] = self.parse_chunk(name, size)
                except ChunkError as e:
                    self.logger.error(f"Error parsing chunk {name} at offset {chunk_start}: {e}")
                    self.skip_chunk(size)
                    
        except Exception as e:
            self.logger.error(f"Error parsing chunks: {e}", exc_info=True)
            raise ParserError(f"Failed to parse chunks: {e}")
            
        return chunks