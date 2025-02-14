# adt_analyzer/chunks/mcin/entry.py
from dataclasses import dataclass
import struct
from typing import Dict, Any

@dataclass
class McinEntry:
    """Single entry in the MCIN chunk.
    
    Contains information about a single MCNK chunk's location and size.
    Each entry is 16 bytes.
    """
    offset: int        # Offset to MCNK chunk
    size: int         # Size of MCNK chunk
    flags: int        # Flags for this chunk
    async_id: int     # Used for asynchronous loading
    
    @classmethod
    def from_bytes(cls, data: bytes, entry_index: int = 0) -> 'McinEntry':
        """Parse a single MCIN entry from bytes."""
        try:
            offset, size, flags, async_id = struct.unpack('<4I', data[:16])
            return cls(offset, size, flags, async_id)
        except struct.error as e:
            raise ValueError(f"Failed to parse MCIN entry {entry_index}: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary format."""
        return {
            'offset': self.offset,
            'size': self.size,
            'flags': self.flags,
            'async_id': self.async_id
        }
