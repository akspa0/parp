from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import struct

# Import simple chunk decoders
from mcnk_subchunk_decoders import (
    MCVTChunk,
    MCNRChunk,
    MCLVChunk,
    MCLQChunk,
    MCRFChunk,
    MCSHChunk,
    MCCVChunk
)

# Import complex chunk processing
from mcnk_chunk_processor import (
    MCNKFlags,
    MCLYFlags,
    decode_mcly,
    decode_mcal,
    MCNKHeader
)

class MCNKChunk:
    """Main MCNK chunk decoder"""
    def __init__(self, data: bytes):
        self.data = data
        self.header = MCNKHeader.from_bytes(data[:128])
        self.chunks = {}
        self._decode_chunks()
        
    def _decode_chunks(self):
        """Decode all chunks in the MCNK data"""
        pos = 0
        while pos < len(self.data):
            if pos + 8 > len(self.data):
                break
                
            # Read chunk header
            chunk_name = self.data[pos:pos+4].decode('ascii')
            chunk_size = struct.unpack('<I', self.data[pos+4:pos+8])[0]
            chunk_data = self.data[pos+8:pos+8+chunk_size]
            
            # Process each chunk type
            if chunk_name == 'MCVT':
                self.chunks[chunk_name] = MCVTChunk.read(chunk_data)
            elif chunk_name == 'MCNR':
                self.chunks[chunk_name] = MCNRChunk.read(chunk_data)
            elif chunk_name == 'MCLY':
                self.chunks[chunk_name] = decode_mcly(chunk_data, 0, chunk_size)
            elif chunk_name == 'MCAL':
                self.chunks[chunk_name] = decode_mcal(chunk_data, 0, chunk_size, self.header.flags)
            elif chunk_name == 'MCLQ':
                self.chunks[chunk_name] = MCLQChunk.read(chunk_data)
            elif chunk_name == 'MCRF':
                self.chunks[chunk_name] = MCRFChunk.read(chunk_data)
            elif chunk_name == 'MCSH':
                self.chunks[chunk_name] = MCSHChunk.read(chunk_data)
            elif chunk_name == 'MCCV':
                self.chunks[chunk_name] = MCCVChunk.read(chunk_data)
            elif chunk_name == 'MCLV':
                self.chunks[chunk_name] = MCLVChunk.read(chunk_data)
                
            # Move to next chunk
            pos += 8 + chunk_size
            # Pad to 4 bytes
            if pos % 4 != 0:
                pos += 4 - (pos % 4)

    def get_height_data(self) -> Optional[List[float]]:
        """Get height data if available"""
        if 'MCVT' in self.chunks:
            return self.chunks['MCVT'].heights
        return None

    def get_normal_data(self) -> Optional[List[Tuple[int, int, int]]]:
        """Get normal data if available"""
        if 'MCNR' in self.chunks:
            return self.chunks['MCNR'].normals
        return None

    def get_layer_info(self) -> Optional[List[Dict]]:
        """Get layer information if available"""
        if 'MCLY' in self.chunks:
            return self.chunks['MCLY']['layers']
        return None

    def get_alpha_maps(self) -> Optional[List[Dict]]:
        """Get alpha map data if available"""
        if 'MCAL' in self.chunks:
            return self.chunks['MCAL']['alpha_maps']
        return None
