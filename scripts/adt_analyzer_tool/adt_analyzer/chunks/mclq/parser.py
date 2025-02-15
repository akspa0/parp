from typing import Dict, Any, List, Tuple
import struct
from ..base import BaseChunk, ChunkParsingError
from .header import MclqHeader

class MclqChunk(BaseChunk):
    """MCLQ (Legacy Water Data) chunk parser.
    
    Contains legacy water information (pre-WotLK).
    Only present in older ADT files or when converted.
    
    Structure:
    - 8 byte header
    - Array of vertices (12 bytes each, xyz floats)
    - Array of faces (12 bytes each, 3 vertex indices)
    """
    
    HEADER_SIZE = 8
    VERTEX_SIZE = 12  # 3 floats * 4 bytes
    FACE_SIZE = 12    # 3 uint32s
    
    def parse(self) -> Dict[str, Any]:
        """Parse MCLQ chunk data."""
        if len(self.data) < self.HEADER_SIZE:
            raise ChunkParsingError(f"MCLQ chunk too small: {len(self.data)} < {self.HEADER_SIZE}")
        
        try:
            # Parse header
            header = MclqHeader.from_bytes(self.data)
            offset = self.HEADER_SIZE
            
            # Parse vertices
            vertices = self._parse_vertices(offset, header.vertex_count)
            offset += header.vertex_count * self.VERTEX_SIZE
            
            # Parse faces
            faces = self._parse_faces(offset, header.face_count)
            
            return {
                **header.to_dict(),
                'vertices': vertices,
                'faces': faces
            }
            
        except struct.error as e:
            raise ChunkParsingError(f"Failed to parse MCLQ data: {e}")
    
    def _parse_vertices(self, offset: int, count: int) -> List[Tuple[float, float, float]]:
        """Parse vertex data starting at offset."""
        if offset + count * self.VERTEX_SIZE > len(self.data):
            raise ChunkParsingError("MCLQ vertex data truncated")
        
        vertices = []
        for i in range(count):
            pos = offset + i * self.VERTEX_SIZE
            vertex = struct.unpack('<3f', self.data[pos:pos + self.VERTEX_SIZE])
            vertices.append(vertex)
        
        return vertices
    
    def _parse_faces(self, offset: int, count: int) -> List[Tuple[int, int, int]]:
        """Parse face data starting at offset."""
        if offset + count * self.FACE_SIZE > len(self.data):
            raise ChunkParsingError("MCLQ face data truncated")
        
        faces = []
        for i in range(count):
            pos = offset + i * self.FACE_SIZE
            indices = struct.unpack('<3I', self.data[pos:pos + self.FACE_SIZE])
            faces.append(indices)
        
        return faces