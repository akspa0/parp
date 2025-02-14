# adt_analyzer/chunks/mclq.py
from typing import Dict, Any, List
import struct
from .base import BaseChunk, ChunkParsingError

class MclqChunk(BaseChunk):
    """MCLQ (Legacy Water Data) chunk parser.
    
    Contains legacy water information (pre-WotLK).
    Only present in older ADT files or when converted.
    """
    
    HEADER_SIZE = 8
    
    def parse(self) -> Dict[str, Any]:
        """Parse MCLQ chunk data."""
        if len(self.data) < self.HEADER_SIZE:
            raise ChunkParsingError(f"MCLQ chunk too small: {len(self.data)} < {self.HEADER_SIZE}")
        
        try:
            # Parse header
            first_vertex_index, n_vertices, n_faces, flags = struct.unpack('<4H', 
                self.data[:self.HEADER_SIZE])
            
            offset = self.HEADER_SIZE
            vertices = []
            faces = []
            
            # Parse vertices
            for _ in range(n_vertices):
                if offset + 12 > len(self.data):
                    raise ChunkParsingError("MCLQ vertex data truncated")
                
                vertex = struct.unpack('<3f', self.data[offset:offset + 12])
                vertices.append(vertex)
                offset += 12
            
            # Parse faces
            for _ in range(n_faces):
                if offset + 12 > len(self.data):
                    raise ChunkParsingError("MCLQ face data truncated")
                
                indices = struct.unpack('<3I', self.data[offset:offset + 12])
                faces.append(indices)
                offset += 12
            
            return {
                'first_vertex': first_vertex_index,
                'vertices': vertices,
                'faces': faces,
                'flags': flags
            }
            
        except struct.error as e:
            raise ChunkParsingError(f"Failed to parse MCLQ data: {e}")
