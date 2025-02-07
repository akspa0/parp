"""MPHD chunk handling for WotLK WoW files."""
from dataclasses import dataclass

from ..base import Chunk


@dataclass
class MphdChunk:
    """MPHD (map header) chunk from WotLK WDT files.
    
    This chunk is 32 bytes and contains map flags.
    Only the first byte is used (1 if WMO-based).
    """
    flags: int = 0

    def to_chunk(self) -> Chunk:
        """Convert to raw chunk format.
        
        Creates a 32-byte chunk with flags in first byte.
        """
        # Create 32 bytes of zeros
        data = bytearray(32)
        
        # Set first byte if WMO-based
        if self.flags & 1:
            data[0] = 1

        return Chunk(letters='DHPM', size=32, data=bytes(data))

    def is_wmo_based(self) -> bool:
        """Check if map is WMO-based."""
        return bool(self.flags & 1)

    @classmethod
    def from_alpha(cls, alpha_mphd: 'AlphaMphdChunk') -> 'MphdChunk':
        """Convert from Alpha format."""
        return cls(flags=1 if alpha_mphd.is_wmo_based() else 0)

    def __str__(self) -> str:
        return f"MPHD Chunk (WMO-based: {self.is_wmo_based()})"