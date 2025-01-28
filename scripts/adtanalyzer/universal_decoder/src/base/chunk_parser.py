import os
import struct
import logging
from typing import Dict, List, Tuple, Optional, Generator, BinaryIO
from dataclasses import dataclass
from ..format_detector import FileFormat, FileType

@dataclass
class ChunkInfo:
    """Information about a parsed chunk"""
    name: bytes
    offset: int
    size: int
    data_offset: int
    format: FileFormat

class ChunkParsingError(Exception):
    """Base exception for chunk parsing errors"""
    pass

class ChunkParser:
    """Base class for parsing chunked WoW data files"""

    CHUNK_HEADER_SIZE = 8

    def __init__(self, file_path: str, file_format: FileFormat, reversed_chunks: bool = False):
        """
        Initialize the chunk parser
        
        Args:
            file_path: Path to the file to parse
            file_format: Format of the file (ALPHA or RETAIL)
            reversed_chunks: Whether chunk names are reversed
        """
        self.file_path = file_path
        self.format = file_format
        self.reversed_chunks = reversed_chunks
        self.file_size = os.path.getsize(file_path)
        self._file: Optional[BinaryIO] = None
        self._chunk_cache: Dict[bytes, List[ChunkInfo]] = {}
        
        # Set up logging
        self.logger = logging.getLogger(self.__class__.__name__)

    def __enter__(self):
        """Context manager entry"""
        self._file = open(self.file_path, 'rb')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self._file:
            self._file.close()
            self._file = None

    def _read_chunk_header(self, offset: int) -> Optional[Tuple[bytes, int]]:
        """
        Read a chunk header at the given offset
        
        Returns:
            Tuple of (chunk_name, chunk_size) or None if EOF
        """
        if not self._file:
            raise RuntimeError("File not opened. Use with context manager.")
            
        self._file.seek(offset)
        header = self._file.read(self.CHUNK_HEADER_SIZE)
        
        if not header or len(header) < self.CHUNK_HEADER_SIZE:
            return None
            
        chunk_name = header[:4]
        if self.reversed_chunks:
            chunk_name = chunk_name[::-1]
            
        chunk_size = struct.unpack('<I', header[4:8])[0]
        return chunk_name, chunk_size

    def _read_chunk_data(self, offset: int, size: int) -> bytes:
        """Read chunk data at offset of given size"""
        if not self._file:
            raise RuntimeError("File not opened. Use with context manager.")
            
        self._file.seek(offset)
        return self._file.read(size)

    def _validate_chunk_size(self, chunk_name: bytes, offset: int, size: int) -> bool:
        """
        Validate that a chunk's size is reasonable
        
        Returns:
            bool: Whether the chunk size is valid
        """
        # Basic size validation
        if size < 0:
            self.logger.error(f"Negative chunk size at offset {offset}")
            return False
            
        if offset + self.CHUNK_HEADER_SIZE + size > self.file_size:
            self.logger.error(f"Chunk {chunk_name} at {offset} extends beyond file end")
            return False
            
        # Format-specific validation could be added here
        return True

    def find_chunks(self, chunk_name: bytes) -> Generator[ChunkInfo, None, None]:
        """
        Find all instances of a chunk type in the file
        
        Args:
            chunk_name: Name of chunk to find (e.g., b'MVER')
            
        Yields:
            ChunkInfo objects for each instance found
        """
        # Check cache first
        if chunk_name in self._chunk_cache:
            yield from self._chunk_cache[chunk_name]
            return

        # Scan file for chunks
        chunks_found = []
        offset = 0
        
        while offset < self.file_size:
            header = self._read_chunk_header(offset)
            if not header:
                break
                
            name, size = header
            
            if not self._validate_chunk_size(name, offset, size):
                offset += self.CHUNK_HEADER_SIZE  # Try to recover
                continue
                
            if name == chunk_name:
                chunk_info = ChunkInfo(
                    name=name,
                    offset=offset,
                    size=size,
                    data_offset=offset + self.CHUNK_HEADER_SIZE,
                    format=self.format
                )
                chunks_found.append(chunk_info)
                yield chunk_info
                
            offset += self.CHUNK_HEADER_SIZE + size

        # Cache results
        self._chunk_cache[chunk_name] = chunks_found

    def read_chunk(self, chunk_info: ChunkInfo) -> bytes:
        """Read the data for a specific chunk"""
        if not self._validate_chunk_size(chunk_info.name, chunk_info.offset, chunk_info.size):
            raise ChunkParsingError(f"Invalid chunk size for {chunk_info.name}")
            
        return self._read_chunk_data(chunk_info.data_offset, chunk_info.size)

    def has_chunk(self, chunk_name: bytes) -> bool:
        """Check if file contains a specific chunk type"""
        try:
            next(self.find_chunks(chunk_name))
            return True
        except StopIteration:
            return False

    def get_chunk_count(self, chunk_name: bytes) -> int:
        """Get the number of instances of a specific chunk type"""
        return sum(1 for _ in self.find_chunks(chunk_name))

    def clear_cache(self):
        """Clear the chunk cache"""
        self._chunk_cache.clear()

    @staticmethod
    def read_padded_string(data: bytes, offset: int = 0) -> Tuple[str, int]:
        """
        Read a null-terminated string from binary data
        
        Returns:
            Tuple of (string, next_offset)
        """
        end = data.find(b'\0', offset)
        if end == -1:
            return data[offset:].decode('utf-8', 'replace'), len(data)
        return data[offset:end].decode('utf-8', 'replace'), end + 1

    @staticmethod
    def read_fixed_string(data: bytes, size: int, offset: int = 0) -> str:
        """Read a fixed-size string, trimming null termination"""
        return data[offset:offset+size].split(b'\0', 1)[0].decode('utf-8', 'replace')

    @staticmethod
    def read_vec3d(data: bytes, offset: int = 0) -> Tuple[float, float, float]:
        """Read a 3D vector (three 32-bit floats)"""
        return struct.unpack('<fff', data[offset:offset+12])

    @staticmethod
    def read_vec2d(data: bytes, offset: int = 0) -> Tuple[float, float]:
        """Read a 2D vector (two 32-bit floats)"""
        return struct.unpack('<ff', data[offset:offset+8])