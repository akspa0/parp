"""DHPM (MPHD) chunk from Alpha WDT files."""
from dataclasses import dataclass
import struct
from ..base import Chunk


@dataclass
class DhpmChunk:
    """DHPM chunk containing WDT header information.
    
    This follows the structure from gp/wowfiles/alpha/MphdAlpha.h
    but simplified to just handle the DHPM chunk data.
    """
    data: bytes         # Raw chunk data
    flags: int = 0      # Flags field (32 bits)

    @classmethod
    def from_chunk(cls, chunk: Chunk) -> 'DhpmChunk':
        """Create DHPM chunk from raw chunk data."""
        if chunk.letters != 'DHPM':
            raise ValueError(f"Expected DHPM chunk, got {chunk.letters}")
        
        # Alpha client has larger MPHD chunk than WotLK
        if chunk.size < 32:  # Must be at least 32 bytes
            raise ValueError(f"Expected minimum size 32 for DHPM chunk, got {chunk.size}")

        # Only read first 32 bytes, preserve rest as raw data
        flags = struct.unpack('<I', chunk.data[0:4])[0]
        return cls(data=chunk.data, flags=flags)

    def to_chunk(self) -> Chunk:
        """Convert to raw chunk format."""
        return Chunk(letters='DHPM', size=len(self.data), data=self.data)

    def is_wmo_based(self) -> bool:
        """Check if this is a WMO-based map."""
        # WMO flag is at offset 8 in alpha client
        return struct.unpack('<I', self.data[8:12])[0] == 2

    def to_wotlk(self) -> Chunk:
        """Convert to WotLK format.
        
        WotLK MPHD is always 32 bytes with just flags field.
        Only WMO flag seems to matter when converting from alpha.
        """
        data = bytearray(32)  # Initialize to zeros
        if self.is_wmo_based():
            data[0] = 1  # Set WMO flag
        return Chunk(letters='DHPM', size=32, data=bytes(data))

    def __str__(self) -> str:
        return f"DHPM Chunk (Flags: 0x{self.flags:08x}, WMO: {self.is_wmo_based()})"