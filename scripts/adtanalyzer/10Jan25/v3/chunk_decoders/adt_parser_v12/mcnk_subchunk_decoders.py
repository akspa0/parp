from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Union
import struct

@dataclass
class MCBBChunk:
    """MCBB (Bounding box) chunk decoder"""
    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float

    @classmethod
    def read(cls, data: bytes) -> 'MCBBChunk':
        """Read MCBB chunk from bytes"""
        min_x, min_y, min_z, max_x, max_y, max_z = struct.unpack('6f', data)
        return cls(min_x=min_x, min_y=min_y, min_z=min_z,
                  max_x=max_x, max_y=max_y, max_z=max_z)

@dataclass
class MCSEChunk:
    """MCSE (Sound emitters) chunk decoder"""
    entries: List[Dict[str, Union[int, Tuple[float, float, float]]]]

    @classmethod
    def read(cls, data: bytes) -> 'MCSEChunk':
        """Read MCSE chunk from bytes"""
        entries = []
        for i in range(0, len(data), 28):
            entry_data = data[i:i+28]
            if len(entry_data) == 28:
                entries.append({
                    'sound_id': struct.unpack_from('<I', entry_data, 0)[0],
                    'sound_type': struct.unpack_from('<I', entry_data, 4)[0],
                    'position': struct.unpack_from('<3f', entry_data, 8),
                    'min_distance': struct.unpack_from('<f', entry_data, 20)[0],
                    'max_distance': struct.unpack_from('<f', entry_data, 24)[0]
                })
        return cls(entries=entries)

@dataclass
class MCRFChunk:
    """MCRF (Doodad references) chunk decoder"""
    entries: List[int]

    @classmethod
    def read(cls, data: bytes) -> 'MCRFChunk':
        """Read MCRF chunk from bytes"""
        entries = list(struct.unpack(f'<{len(data)//4}I', data))
        return cls(entries=entries)

@dataclass
class MCLQChunk:
    """MCLQ (Liquid data) chunk decoder"""
    liquid_vertices: List[Dict[str, Union[float, int]]]
    liquid_tiles: List[int]
    flags: Optional[List[int]] = None

    @classmethod
    def read(cls, data: bytes) -> 'MCLQChunk':
        """Read MCLQ chunk from bytes"""
        # First 8 bytes per vertex: height, render flags
        vertices = []
        pos = 0
        while pos + 8 <= len(data):
            vertex = {
                'height': struct.unpack_from('<f', data, pos)[0],
                'render_flags': struct.unpack_from('<I', data, pos + 4)[0]
            }
            vertices.append(vertex)
            pos += 8
            
        # Then liquid tile flags
        tiles = []
        while pos + 1 <= len(data):
            tiles.append(data[pos])
            pos += 1
            
        return cls(liquid_vertices=vertices, liquid_tiles=tiles)

@dataclass
class MCLYChunk:
    """MCLY (Layer info) chunk decoder"""
    textureId: int
    flags: int
    offsetInMCAL: int
    effectId: int

    @classmethod
    def read(cls, data: bytes) -> List['MCLYChunk']:
        """Read MCLY chunk from bytes"""
        layers = []
        for i in range(0, len(data), 16):  # Each layer entry is 16 bytes
            chunk_data = data[i:i+16]
            if len(chunk_data) == 16:
                textureId, flags, offsetInMCAL, effectId = struct.unpack('4i', chunk_data)
                layers.append(cls(
                    textureId=textureId,
                    flags=flags,
                    offsetInMCAL=offsetInMCAL,
                    effectId=effectId
                ))
        return layers

@dataclass
class MCALChunk:
    """MCAL (Alpha maps) chunk decoder"""
    alpha_map: bytes

    @classmethod
    def read(cls, data: bytes, mcly_chunks: List[MCLYChunk] = None) -> Dict[int, 'MCALChunk']:
        """
        Read MCAL chunk from bytes and associate with texture layers
        Args:
            data: Raw MCAL chunk data
            mcly_chunks: List of MCLY chunks to get offset information
        Returns:
            Dictionary mapping texture IDs to their alpha maps
        """
        alpha_maps = {}
        if mcly_chunks:
            for i, layer in enumerate(mcly_chunks):
                if i == 0:  # Base layer doesn't have alpha map
                    continue
                    
                # Get alpha map data using offset from MCLY
                start = layer.offsetInMCAL
                # If this is the last layer, read until the end, otherwise read until next layer
                end = len(data) if i == len(mcly_chunks) - 1 else mcly_chunks[i + 1].offsetInMCAL
                alpha_map = data[start:end]
                alpha_maps[layer.textureId] = cls(alpha_map=alpha_map)
                
        return alpha_maps

@dataclass
class MCVTChunk:
    """MCVT (Vertex Heights) chunk decoder"""
    heights: List[float]

    @classmethod
    def read(cls, data: bytes) -> 'MCVTChunk':
        """Read MCVT chunk from bytes"""
        heights = list(struct.unpack('145f', data))
        return cls(heights=heights)

@dataclass
class MCNRChunk:
    """MCNR (Normal vectors) chunk decoder"""
    normals: List[Tuple[int, int, int]]

    @classmethod
    def read(cls, data: bytes) -> 'MCNRChunk':
        """Read MCNR chunk from bytes"""
        normals = []
        for i in range(0, len(data), 3):
            normal = struct.unpack('3b', data[i:i+3])
            normals.append(normal)
        return cls(normals=normals)

@dataclass
class MCLVChunk:
    """MCLV (Light values) chunk decoder"""
    values: List[int]

    @classmethod
    def read(cls, data: bytes) -> 'MCLVChunk':
        values = list(struct.unpack(f'{len(data)}B', data))
        return cls(values=values)

@dataclass
class MCLQChunk:
    """MCLQ (Legacy liquid) chunk decoder"""
    liquid_type: int
    height_data: List[float]
    flags: List[int]
    
    @classmethod
    def read(cls, data: bytes) -> 'MCLQChunk':
        liquid_type = struct.unpack('i', data[0:4])[0]
        heights = []
        pos = 4
        for _ in range(81):
            height = struct.unpack('f', data[pos:pos+4])[0]
            heights.append(height)
            pos += 4
        flags = list(data[pos:])
        return cls(liquid_type=liquid_type, height_data=heights, flags=flags)

@dataclass
class MCRFChunk:
    """MCRF (Render flags) chunk decoder"""
    flags: List[int]

    @classmethod
    def read(cls, data: bytes) -> 'MCRFChunk':
        flags = list(struct.unpack(f'{len(data)}B', data))
        return cls(flags=flags)

@dataclass
class MCSHChunk:
    """MCSH (Shadow map) chunk decoder"""
    shadow_map: List[int]

    @classmethod
    def read(cls, data: bytes) -> 'MCSHChunk':
        shadow_map = list(struct.unpack(f'{len(data)}B', data))
        return cls(shadow_map=shadow_map)

@dataclass
class MCCVChunk:
    """MCCV (Vertex colors) chunk decoder"""
    vertex_colors: List[Tuple[int, int, int, int]]

    @classmethod
    def read(cls, data: bytes) -> 'MCCVChunk':
        colors = []
        for i in range(0, len(data), 4):
            color = struct.unpack('4B', data[i:i+4])
            colors.append(color)
        return cls(vertex_colors=colors)
