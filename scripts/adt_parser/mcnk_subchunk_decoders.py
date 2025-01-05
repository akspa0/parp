#!/usr/bin/env python3
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import struct
from enum import IntFlag
import numpy as np

class MCLYFlags(IntFlag):
    """MCLY chunk flags"""
    USE_ALPHA_MAP = 0x1
    ALPHA_COMPRESSED = 0x2
    USE_CUBE_MAP_ENV = 0x4
    UNK8 = 0x8
    UNK10 = 0x10
    UNK20 = 0x20
    UNK40 = 0x40
    UNK80 = 0x80
    UNK100 = 0x100
    TEXTURE_ANIMATED = 0x200

@dataclass
class TextureLayer:
    """Texture layer definition from MCLY"""
    texture_id: int
    flags: MCLYFlags
    offset_mcal: int
    effect_id: int
    layer_id: int = 0    # Added in Cata
    compressed_size: int = 0  # Only if ALPHA_COMPRESSED
    
    @classmethod
    def from_bytes(cls, data: bytes, version: int) -> 'TextureLayer':
        if version >= 8: # Cata+
            tex_id, flags, offset, effect_id, layer_id = struct.unpack('<IIIIH', data[:18])
            return cls(tex_id, MCLYFlags(flags), offset, effect_id, layer_id)
        else:
            tex_id, flags, offset, effect_id = struct.unpack('<IIII', data[:16])
            return cls(tex_id, MCLYFlags(flags), offset, effect_id)

class MCVTChunk:
    """Height map vertex data"""
    def __init__(self, data: bytes):
        self.height_map: List[float] = []
        self._parse(data)

    def _parse(self, data: bytes):
        # 145 vertices per chunk (9*9 + 8*8)
        num_heights = 145
        for i in range(num_heights):
            height = struct.unpack('f', data[i*4:i*4+4])[0]
            self.height_map.append(height)

    def get_height(self, x: int, y: int) -> float:
        """Get height at grid position"""
        if 0 <= x < 9 and 0 <= y < 9:
            return self.height_map[y * 17 + x]
        return 0.0

class MCNRChunk:
    """Normal data for vertices"""
    def __init__(self, data: bytes):
        self.normals: List[Tuple[float, float, float]] = []
        self._parse(data)

    def _parse(self, data: bytes):
        # 145 normals per chunk (9*9 + 8*8)
        num_normals = 145
        for i in range(num_normals):
            offset = i * 3
            x, y, z = struct.unpack('3B', data[offset:offset+3])
            # Convert from signed byte to float (-1 to 1)
            self.normals.append((
                (x - 127) / 127,
                (y - 127) / 127,
                (z - 127) / 127
            ))

class MCLYChunk:
    """Texture layer definitions"""
    def __init__(self, data: bytes, version: int):
        self.layers: List[TextureLayer] = []
        self._parse(data, version)

    def _parse(self, data: bytes, version: int):
        layer_size = 18 if version >= 8 else 16
        num_layers = len(data) // layer_size
        
        for i in range(num_layers):
            offset = i * layer_size
            layer = TextureLayer.from_bytes(data[offset:offset+layer_size], version)
            self.layers.append(layer)

class MCALChunk:
    """Alpha maps for texture layers"""
    def __init__(self, data: bytes, mcly_chunk: Optional[MCLYChunk] = None):
        self.alpha_maps: List[bytes] = []
        self._parse(data, mcly_chunk)

    def _parse(self, data: bytes, mcly_chunk: Optional[MCLYChunk]):
        if not mcly_chunk:
            return

        current_pos = 0
        for layer in mcly_chunk.layers:
            if layer.flags & MCLYFlags.USE_ALPHA_MAP:
                if layer.flags & MCLYFlags.ALPHA_COMPRESSED:
                    size = layer.compressed_size
                else:
                    size = 4096  # 64*64 alpha map
                
                alpha_data = data[current_pos:current_pos+size]
                self.alpha_maps.append(alpha_data)
                current_pos += size

    def get_alpha_map(self, layer_index: int) -> Optional[bytes]:
        """Get alpha map for specific layer"""
        if 0 <= layer_index < len(self.alpha_maps):
            return self.alpha_maps[layer_index]
        return None

class MCSHChunk:
    """Shadow map data"""
    def __init__(self, data: bytes):
        self.shadow_map: bytes = data

    def get_shadow(self, x: int, y: int) -> int:
        """Get shadow value at position"""
        if 0 <= x < 64 and 0 <= y < 64:
            return self.shadow_map[y * 64 + x]
        return 0

class MCCVChunk:
    """Vertex colors"""
    def __init__(self, data: bytes):
        self.vertex_colors: List[Tuple[int, int, int, int]] = []
        self._parse(data)

    def _parse(self, data: bytes):
        num_vertices = len(data) // 4
        for i in range(num_vertices):
            offset = i * 4
            b, g, r, a = struct.unpack('4B', data[offset:offset+4])
            self.vertex_colors.append((r, g, b, a))

class MCLVChunk:
    """Light values"""
    def __init__(self, data: bytes):
        self.light_values: List[bytes] = []
        self._parse(data)

    def _parse(self, data: bytes):
        # Store raw light data for now
        self.light_values = data

class MCRFChunk:
    """M2/WMO model references"""
    def __init__(self, data: bytes):
        self.refs: List[int] = []
        self._parse(data)

    def _parse(self, data: bytes):
        num_refs = len(data) // 4
        for i in range(num_refs):
            ref = struct.unpack('<I', data[i*4:i*4+4])[0]
            self.refs.append(ref)

def example_usage():
    """Example usage of all MCNK sub-chunks"""
    # Create example height data (MCVT)
    mcvt_data = bytearray()
    for i in range(145):
        mcvt_data.extend(struct.pack('f', i * 0.5))  # Sample heights
    
    # Create example normal data (MCNR)
    mcnr_data = bytearray()
    for i in range(145):
        mcnr_data.extend(struct.pack('3B', 127, 127, 255))  # Mostly upward normals
    
    # Create example texture layer data (MCLY)
    mcly_data = bytearray()
    # Two layers: one base, one with alpha
    mcly_data.extend(struct.pack('<IIIIH', 
        0,  # texture_id
        0,  # flags
        0,  # offset
        0,  # effect_id
        0   # layer_id
    ))
    mcly_data.extend(struct.pack('<IIIIH',
        1,  # texture_id
        int(MCLYFlags.USE_ALPHA_MAP),  # flags
        0,  # offset
        0,  # effect_id
        1   # layer_id
    ))
    
    # Create example alpha map data (MCAL)
    mcal_data = bytes([128] * 4096)  # 64x64 alpha map with 50% opacity
    
    # Create example shadow map data (MCSH)
    mcsh_data = bytes([255] * 4096)  # 64x64 fully shadowed
    
    # Create example vertex color data (MCCV)
    mccv_data = bytearray()
    for i in range(145):
        mccv_data.extend(struct.pack('4B', 255, 255, 255, 255))  # White vertices
    
    # Create example light data (MCLV)
    mclv_data = bytes([128] * 512)  # Example light values
    
    # Create example reference data (MCRF)
    mcrf_data = struct.pack('<3I', 1000, 1001, 1002)  # Three model references
    
    # Parse all chunks
    mcvt_chunk = MCVTChunk(mcvt_data)
    mcnr_chunk = MCNRChunk(mcnr_data)
    mcly_chunk = MCLYChunk(mcly_data, version=8)
    mcal_chunk = MCALChunk(mcal_data, mcly_chunk)
    mcsh_chunk = MCSHChunk(mcsh_data)
    mccv_chunk = MCCVChunk(mccv_data)
    mclv_chunk = MCLVChunk(mclv_data)
    mcrf_chunk = MCRFChunk(mcrf_data)
    
    # Display results
    print("MCVT (Height) Data:")
    print(f"  First 5 heights: {mcvt_chunk.height_map[:5]}")
    
    print("\nMCNR (Normal) Data:")
    print(f"  First 5 normals: {mcnr_chunk.normals[:5]}")
    
    print("\nMCLY (Texture Layers):")
    for i, layer in enumerate(mcly_chunk.layers):
        print(f"  Layer {i}:")
        print(f"    Texture ID: {layer.texture_id}")
        print(f"    Flags: {layer.flags}")
        print(f"    Uses Alpha: {bool(layer.flags & MCLYFlags.USE_ALPHA_MAP)}")
    
    print("\nMCAL (Alpha Maps):")
    print(f"  Number of alpha maps: {len(mcal_chunk.alpha_maps)}")
    
    print("\nMCSH (Shadow Map):")
    print(f"  Shadow map size: {len(mcsh_chunk.shadow_map)} bytes")
    
    print("\nMCCV (Vertex Colors):")
    print(f"  First 5 colors: {mccv_chunk.vertex_colors[:5]}")
    
    print("\nMCLV (Light Values):")
    print(f"  Light data size: {len(mclv_chunk.light_values)} bytes")
    
    print("\nMCRF (Model References):")
    print(f"  References: {mcrf_chunk.refs}")

if __name__ == "__main__":
    example_usage()
