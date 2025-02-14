# adt_analyzer/chunks/base.py
from dataclasses import dataclass
from typing import Any, Dict, Optional, List, Tuple
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

# adt_analyzer/chunks/mver.py
from typing import Dict, Any
import struct
from .base import BaseChunk, ChunkParsingError

class MverChunk(BaseChunk):
    """MVER (Version) chunk parser."""
    
    EXPECTED_SIZE = 4
    
    def parse(self) -> Dict[str, Any]:
        """Parse MVER chunk data.
        Returns version number of the ADT file."""
        if len(self.data) != self.EXPECTED_SIZE:
            raise ChunkParsingError(f"MVER chunk size {len(self.data)} != {self.EXPECTED_SIZE}")
        
        version = struct.unpack('<I', self.data)[0]
        return {
            'version': version
        }

# adt_analyzer/chunks/mhdr.py
from typing import Dict, Any
import struct
from .base import BaseChunk, ChunkParsingError

class MhdrChunk(BaseChunk):
    """MHDR (Header) chunk parser.
    
    Contains offsets to other chunks in the file.
    Size is always 64 bytes.
    """
    
    EXPECTED_SIZE = 64
    
    def parse(self) -> Dict[str, Any]:
        """Parse MHDR chunk data."""
        if len(self.data) != self.EXPECTED_SIZE:
            raise ChunkParsingError(f"MHDR chunk size {len(self.data)} != {self.EXPECTED_SIZE}")
        
        # Unpack all offsets
        offsets = struct.unpack('<16I', self.data)
        
        return {
            'flags': offsets[0],
            'mcin_offset': offsets[1],  # Offset to MCIN chunk
            'mtex_offset': offsets[2],  # Offset to MTEX chunk
            'mmdx_offset': offsets[3],  # Offset to MMDX chunk
            'mmid_offset': offsets[4],  # Offset to MMID chunk
            'mwmo_offset': offsets[5],  # Offset to MWMO chunk
            'mwid_offset': offsets[6],  # Offset to MWID chunk
            'mddf_offset': offsets[7],  # Offset to MDDF chunk
            'modf_offset': offsets[8],  # Offset to MODF chunk
            'mfbo_offset': offsets[9],  # Offset to MFBO chunk
            'mh2o_offset': offsets[10], # Offset to MH2O chunk
            'mtxf_offset': offsets[11], # Offset to MTXF chunk
            'padding': offsets[12:],    # Unused padding
        }

# adt_analyzer/chunks/mtex.py
from typing import Dict, Any, List
from .base import BaseChunk

class MtexChunk(BaseChunk):
    """MTEX (Texture) chunk parser.
    
    Contains a list of null-terminated texture filenames.
    """
    
    def parse(self) -> Dict[str, Any]:
        """Parse MTEX chunk data."""
        # Split on null bytes and decode each string
        texture_list = self.data.split(b'\0')
        textures = [tex.decode('utf-8', 'replace') for tex in texture_list if tex]
        
        return {
            'textures': textures,
            'count': len(textures)
        }

# adt_analyzer/chunks/mmdx.py
from typing import Dict, Any, List
from .base import BaseChunk

class MmdxChunk(BaseChunk):
    """MMDX (M2 Model Filename) chunk parser.
    
    Contains a list of null-terminated M2 model filenames.
    Used in conjunction with MMID chunk which provides offsets.
    """
    
    def parse(self) -> Dict[str, Any]:
        """Parse MMDX chunk data.
        Returns raw block for processing with MMID offsets."""
        return {
            'model_name_block': self.data,
            'size': len(self.data)
        }

# adt_analyzer/chunks/mmid.py
from typing import Dict, Any, List
import struct
from .base import BaseChunk, ChunkParsingError

class MmidChunk(BaseChunk):
    """MMID (M2 Model Offset) chunk parser.
    
    Contains offsets into the MMDX chunk for model filenames.
    Each entry is a uint32 offset.
    """
    
    def parse(self) -> Dict[str, Any]:
        """Parse MMID chunk data."""
        if len(self.data) % 4 != 0:
            raise ChunkParsingError(f"MMID chunk size {len(self.data)} not divisible by 4")
        
        count = len(self.data) // 4
        offsets = struct.unpack(f'<{count}I', self.data)
        
        return {
            'offsets': list(offsets),
            'count': count
        }

# adt_analyzer/chunks/mddf.py
from typing import Dict, Any, List
import struct
from .base import BaseChunk, ChunkParsingError

class MddfChunk(BaseChunk):
    """MDDF (M2 Model Placement) chunk parser.
    
    Contains information about M2 model placement in the map.
    Each entry is 36 bytes.
    """
    
    ENTRY_SIZE = 36
    
    def parse(self) -> Dict[str, Any]:
        """Parse MDDF chunk data."""
        if len(self.data) % self.ENTRY_SIZE != 0:
            raise ChunkParsingError(
                f"MDDF chunk size {len(self.data)} not divisible by {self.ENTRY_SIZE}"
            )
        
        count = len(self.data) // self.ENTRY_SIZE
        entries = []
        
        for i in range(count):
            entry_data = self.data[i*self.ENTRY_SIZE:(i+1)*self.ENTRY_SIZE]
            
            # Unpack the entry
            (mmid_entry, unique_id,
             pos_x, pos_y, pos_z,
             rot_x, rot_y, rot_z,
             scale, flags) = struct.unpack('<2I6fHH', entry_data)
            
            entries.append({
                'mmid_entry': mmid_entry,
                'unique_id': unique_id,
                'position': (pos_x, pos_y, pos_z),
                'rotation': (rot_x, rot_y, rot_z),
                'scale': scale / 1024.0,  # Scale is stored as fixed-point
                'flags': flags
            })
        
        return {
            'entries': entries,
            'count': count
        }
