from dataclasses import dataclass
from typing import Dict

@dataclass
class MclqHeader:
    """MCLQ (Legacy Water Data) header.
    
    Contains information about the water mesh structure.
    Total size: 8 bytes
    """
    first_vertex_index: int  # Index of first vertex
    vertex_count: int       # Number of vertices
    face_count: int        # Number of faces
    flags: int            # Water flags

    @classmethod
    def from_bytes(cls, data: bytes) -> 'MclqHeader':
        """Create header from bytes."""
        import struct
        first_vertex, n_vertices, n_faces, flags = struct.unpack('<4H', data[:8])
        return cls(
            first_vertex_index=first_vertex,
            vertex_count=n_vertices,
            face_count=n_faces,
            flags=flags
        )

    def to_dict(self) -> Dict:
        """Convert header to dictionary."""
        return {
            'first_vertex': self.first_vertex_index,
            'vertex_count': self.vertex_count,
            'face_count': self.face_count,
            'flags': self.flags
        }