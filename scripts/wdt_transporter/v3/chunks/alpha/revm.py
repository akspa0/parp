"""REVM (MVER) chunk from Alpha WDT files."""
from dataclasses import dataclass
import struct
from ..base import Chunk


@dataclass
class RevmChunk:
    """REVM chunk containing version information.
    
    This follows the structure from gp/wowfiles/alpha/WdtAlpha.h
    but simplified to just handle the REVM chunk data.
    """
    version: int = 0  # Always 18 (0x12) in alpha client

    @classmethod
    def from_chunk(cls, chunk: Chunk) -> 'RevmChunk':
        """Create REVM chunk from raw chunk data."""
        if chunk.letters != 'REVM':
            raise ValueError(f"Expected REVM chunk, got {chunk.letters}")
        
        if chunk.size != 4:
            raise ValueError(f"Expected size 4 for REVM chunk, got {chunk.size}")

        version = struct.unpack('<I', chunk.data)[0]
        return cls(version=version)

    def to_chunk(self) -> Chunk:
        """Convert to raw chunk format."""
        data = struct.pack('<I', self.version)
        return Chunk(letters='REVM', size=4, data=data)

    def __str__(self) -> str:
        return f"REVM Chunk (Version: {self.version})"