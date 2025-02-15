# adt_analyzer/chunks/base.py
from dataclasses import dataclass
from typing import Any, Dict, Optional
import struct
import logging

logger = logging.getLogger(__name__)

@dataclass
class ChunkHeader:
    """Base class for chunk headers."""
    name: bytes
    size: int
    offset: int  # Added to help with offset tracking
    
    @classmethod
    def from_bytes(cls, data: bytes, offset: int = 0) -> 'ChunkHeader':
        """Create chunk header from bytes."""
        name = data[offset:offset+4]
        size = struct.unpack('<I', data[offset+4:offset+8])[0]
        return cls(name=name, size=size, offset=offset)

@dataclass
class BaseChunk:
    """Base class for all chunks."""
    header: ChunkHeader
    data: bytes
    
    @classmethod
    def from_bytes(cls, data: bytes, offset: int = 0) -> Optional['BaseChunk']:
        """Create chunk from bytes."""
        try:
            header = ChunkHeader.from_bytes(data, offset)
            chunk_data = data[offset+8:offset+8+header.size]
            return cls(header=header, data=chunk_data)
        except Exception as e:
            logger.error(f"Failed to parse chunk at offset {offset}: {e}")
            return None
    
    def parse(self) -> Dict[str, Any]:
        """Parse chunk data into dictionary. Override in subclasses."""
        return {'raw_data': self.data}

class ChunkParsingError(Exception):
    """Raised when chunk parsing fails."""
    pass
