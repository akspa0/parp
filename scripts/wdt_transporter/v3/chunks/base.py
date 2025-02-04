"""Base chunk handling for WoW file formats."""
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Optional
import struct


@dataclass
class Chunk:
    """Base chunk class that preserves raw chunk data and magic values.
    
    This follows the structure from gp/wowfiles/Chunk.h but simplified for Python.
    Key differences:
    - Uses raw chunk identifiers (e.g. 'REVM' not 'MVER')
    - Stores data as bytes instead of vector<char>
    - No inheritance from WowChunkedFormat
    """
    letters: str  # Raw 4-letter chunk identifier (e.g. 'REVM')
    size: int    # Size of chunk data
    data: bytes  # Raw chunk data

    @classmethod
    def read(cls, f: BinaryIO) -> Optional['Chunk']:
        """Read a chunk from a binary file.
        
        Returns None if no more chunks can be read (EOF).
        Raises ValueError if chunk data is incomplete.
        """
        # Read chunk header (4 bytes magic + 4 bytes size)
        header = f.read(8)
        if not header or len(header) < 8:
            return None

        # Get magic letters directly from file
        letters = header[:4].decode('ascii')
        size = struct.unpack('<I', header[4:8])[0]

        # Read chunk data
        data = f.read(size)
        if len(data) < size:
            raise ValueError(f"Incomplete chunk data for {letters}")

        return cls(letters=letters, size=size, data=data)

    def write(self, f: BinaryIO) -> None:
        """Write chunk to a binary file."""
        # Write chunk header
        f.write(self.letters.encode('ascii'))
        f.write(struct.pack('<I', self.size))
        # Write chunk data
        f.write(self.data)

    @property
    def real_size(self) -> int:
        """Get actual size of chunk data."""
        return len(self.data)

    def get_int(self, offset: int) -> int:
        """Get 32-bit integer from chunk data at given offset."""
        return struct.unpack('<I', self.data[offset:offset+4])[0]

    def get_string(self, offset: int, size: int) -> str:
        """Get string from chunk data at given offset."""
        return self.data[offset:offset+size].decode('ascii')

    def __str__(self) -> str:
        return f"Chunk letters: {self.letters}\n" \
               f"Chunk size: {self.size}\n" \
               f"Real size: {self.real_size}\n" \
               f"------------------------------"