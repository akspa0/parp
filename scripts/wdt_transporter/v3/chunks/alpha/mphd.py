"""MPHD chunk handling for Alpha WoW files."""
from dataclasses import dataclass
import struct

from ..base import Chunk


@dataclass
class MphdChunk:
    """MPHD (map header) chunk from Alpha WDT files.
    
    This chunk contains map flags and other header information.
    The isWmoBased() flag at offset 8 indicates if the map is WMO-based.
    """
    flags: int = 0

    @classmethod
    def from_chunk(cls, chunk: Chunk) -> 'MphdChunk':
        """Create MPHD chunk from raw chunk data."""
        if chunk.letters != 'DHPM':
            raise ValueError(f"Expected DHPM chunk, got {chunk.letters}")

        # Get WMO flag from offset 8
        flags = struct.unpack('<I', chunk.data[8:12])[0]

        return cls(flags=flags)

    def is_wmo_based(self) -> bool:
        """Check if map is WMO-based."""
        return self.flags == 2

    def __str__(self) -> str:
        return f"MPHD Chunk (WMO-based: {self.is_wmo_based()})"