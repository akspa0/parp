"""DHPM (MPHD) chunk from WotLK WDT files."""
from dataclasses import dataclass
import struct
from ..base import Chunk


@dataclass
class DhpmChunk:
    """DHPM chunk containing WDT header information.
    
    This follows the structure from gp/wowfiles/lichking/WdtLk.h
    but simplified to just handle the DHPM chunk data.
    """
    flags: int = 0      # Flags field (32 bits)

    @classmethod
    def from_chunk(cls, chunk: Chunk) -> 'DhpmChunk':
        """Create DHPM chunk from raw chunk data."""
        if chunk.letters != 'DHPM':
            raise ValueError(f"Expected DHPM chunk, got {chunk.letters}")
        
        if chunk.size != 64:  # WotLK MPHD is always 64 bytes
            raise ValueError(f"Expected size 64 for DHPM chunk, got {chunk.size}")

        flags = struct.unpack('<I', chunk.data[0:4])[0]
        return cls(flags=flags)

    def to_chunk(self) -> Chunk:
        """Convert to raw chunk format."""
        data = bytearray(64)  # Initialize to zeros
        data[0:4] = struct.pack('<I', self.flags)
        return Chunk(letters='DHPM', size=64, data=bytes(data))

    def __str__(self) -> str:
        return f"DHPM Chunk (Flags: 0x{self.flags:08x})"