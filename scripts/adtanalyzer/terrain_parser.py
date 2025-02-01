"""
Base parser for WoW terrain files.
Provides common functionality for both ADT and WDT parsing.
"""
import os
import struct
import logging
from typing import BinaryIO, Dict, Generator, List, Optional, Tuple, Union
from pathlib import Path
from terrain_structures import ChunkInfo, TerrainFile

class ParsingError(Exception):
    """Base class for parsing errors"""
    pass

class ChunkError(ParsingError):
    """Error related to chunk parsing"""
    pass

class TerrainParser:
    """Base class for terrain file parsing"""
    
    # Common chunk names
    MVER = b'MVER'  # Version information
    MHDR = b'MHDR'  # Header information
    MCNK = b'MCNK'  # Map chunk
    MTEX = b'MTEX'  # Texture filenames
    MMDX = b'MMDX'  # M2 model filenames (Retail)
    MMID = b'MMID'  # M2 model indices (Retail)
    MWMO = b'MWMO'  # WMO model filenames (Retail)
    MWID = b'MWID'  # WMO model indices (Retail)
    MDDF = b'MDDF'  # M2 placements
    MODF = b'MODF'  # WMO placements
    MAIN = b'MAIN'  # Main array (WDT)
    MPHD = b'MPHD'  # Map header (WDT)
    MDNM = b'MDNM'  # M2 model filenames (Alpha)
    MONM = b'MONM'  # WMO model filenames (Alpha)
    
    def __init__(self, file_path: str):
        """
        Initialize parser
        
        Args:
            file_path: Path to file to parse
        """
        self.file_path = Path(file_path)
        self._file: Optional[BinaryIO] = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chunk_order: List[str] = []
        self.reverse_names = False
        
    def __enter__(self):
        """Context manager entry"""
        self.open()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        
    def open(self):
        """Open file for reading"""
        if self._file is None:
            try:
                self._file = open(self.file_path, 'rb')
                # Detect chunk name orientation
                self.reverse_names = self._detect_chunk_reversal()
            except OSError as e:
                raise ParsingError(f"Failed to open {self.file_path}: {e}")
                
    def close(self):
        """Close file if open"""
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
            if self.reverse_names:
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
        data = self.read_bytes(chunk.size)
        
        return data
        
    def _try_parse_chunks(self, data: bytes, reverse_names: bool = False) -> List[Tuple[bytes, bytes]]:
        """Try to parse first few chunks"""
        pos = 0
        size = len(data)
        chunks = []
        while pos + 8 <= size:
            chunk_name = data[pos:pos+4]
            if reverse_names:
                chunk_name = chunk_name[::-1]
            chunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]
            if pos + 8 + chunk_size > size:
                break
            chunk_data = data[pos+8:pos+8+chunk_size]
            chunks.append((chunk_name, chunk_data))
            pos += 8 + chunk_size
            if len(chunks) > 10:  # Only need first few chunks
                break
        return chunks
        
    def _detect_chunk_reversal(self) -> bool:
        """Detect if chunk names are reversed"""
        if self._file is None:
            raise ParsingError("File not open")
            
        # Read first part of file
        self._file.seek(0)
        data = self._file.read(1024)  # Read first KB
        
        # Try parsing both ways
        normal_chunks = self._try_parse_chunks(data, False)
        reversed_chunks = self._try_parse_chunks(data, True)
        
        # Look for known chunk names
        known_chunks = {self.MVER, self.MHDR, self.MCNK, self.MTEX, self.MAIN, self.MPHD}
        
        normal_known = any(name in known_chunks for name, _ in normal_chunks)
        reversed_known = any(name in known_chunks for name, _ in reversed_chunks)
        
        if normal_known and not reversed_known:
            return False
        elif reversed_known and not normal_known:
            return True
            
        # Default to normal if can't determine
        return False
        
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
                
            # Track chunk order
            self.chunk_order.append(chunk_magic.decode('ascii', errors='ignore'))
                
            # Create chunk info
            chunk = ChunkInfo(
                name=chunk_magic,
                offset=chunk_start,
                size=chunk_size,
                data_offset=chunk_start + 8
            )
            
            # Check if chunk matches requested magic
            if magic is None or chunk.name == magic:
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
            
    def parse(self) -> TerrainFile:
        """
        Parse terrain file
        
        Returns:
            Parsed terrain file data
            
        This method must be implemented by subclasses
        """
        raise NotImplementedError