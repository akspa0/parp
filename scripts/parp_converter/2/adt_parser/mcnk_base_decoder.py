#!/usr/bin/env python3
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import struct
from enum import IntFlag

from mcnk_subchunk_decoders import (
    MCVTChunk, MCNRChunk, MCLYChunk, MCALChunk,
    MCSHChunk, MCCVChunk, MCLVChunk, MCRFChunk
)

class MCNKFlags(IntFlag):
    """MCNK flags from header"""
    HAS_MCSH = 0x1            # Shadow map present
    IMPASS = 0x2              # Impassable terrain
    LQ_RIVER = 0x4            # River in terrain
    LQ_OCEAN = 0x8            # Ocean in terrain
    LQ_MAGMA = 0x10           # Magma in terrain
    LQ_SLIME = 0x20           # Slime in terrain
    HAS_MCCV = 0x40           # Vertex colors present
    UNK80 = 0x80
    DO_NOT_FIX_ALPHA_MAP = 0x100
    HAS_AREA_ID = 0x200
    HAS_HEIGHT = 0x400        # Height for liquid surface
    UNK800 = 0x800
    LQ_WATER = 0x1000         # Water / River (hack)
    HAS_VERTEX_SHADING = 0x2000 # Vertex shading (shadows)
    UNK4000 = 0x4000
    HAS_BIG_ALPHA = 0x8000    # Extended alpha
    UNK10000 = 0x10000
    HAS_DOODAD_REFS = 0x20000  # M2/WMO refs present
    MCLV_HAS_2_VALUES = 0x40000 # 2 Light values per vertex
    HAS_MCLV = 0x80000        # Light values present

@dataclass
class MCNKHeader:
    """MCNK chunk header"""
    flags: MCNKFlags
    idx_x: int
    idx_y: int
    n_layers: int
    n_doodad_refs: int
    holes: int
    layer_alpha_1: int        # Low-resolution (base) alpha
    area_id: int
    n_sound_emitters: int
    n_sound_emitter_files: int
    liquid_level: float
    pred_tex: int             # Index for tex coords prediction
    n_effect_doodad: int      # BFA+: unused
    holes_high: int           # Legion+: Additional holes mask
    offset_mcly: int          # MCLY offset (relative to chunk start)
    offset_mcrf: int          # MCRF offset
    offset_mcal: int          # MCAL offset
    size_mcal: int            # MCAL size
    offset_mcsh: int          # MCSH offset
    size_mcsh: int            # MCSH size
    area_id_2: int           # BFA+: area ID (previously padding)
    offset_mcal_2: int       # BFA+: MCAL offset (prev padding)
    flags_2: int             # BFA+: additional flags
    pad_3: int
    offset_mclv: int         # MCLV offset
    flags_3: int             # Counter for BFA+ alpha
    offset_mccv: int         # MCCV offset
    offset_mclq: Optional[int] = None  # Pre-Cata: MCLQ offset
    offset_mcse: Optional[int] = None  # Pre-Cata: MCSE offset

    @classmethod
    def from_bytes(cls, data: bytes, version: int) -> 'MCNKHeader':
        if version >= 8:  # Cata+
            (flags, idx_x, idx_y, n_layers, n_doodad_refs, holes,
             layer_alpha_1, area_id, n_sound_emitters, n_sound_emitter_files,
             liquid_level, pred_tex, n_effect_doodad, holes_high,
             offset_mcly, offset_mcrf, offset_mcal, size_mcal,
             offset_mcsh, size_mcsh, area_id_2, offset_mcal_2,
             flags_2, pad_3, offset_mclv, flags_3,
             offset_mccv) = struct.unpack('<IIIIIIIIIIFFIIIIIIIIIIIIIII', data[:108])
            
            return cls(
                MCNKFlags(flags), idx_x, idx_y, n_layers, n_doodad_refs,
                holes, layer_alpha_1, area_id, n_sound_emitters,
                n_sound_emitter_files, liquid_level, pred_tex,
                n_effect_doodad, holes_high, offset_mcly, offset_mcrf,
                offset_mcal, size_mcal, offset_mcsh, size_mcsh,
                area_id_2, offset_mcal_2, flags_2, pad_3,
                offset_mclv, flags_3, offset_mccv
            )
        else:  # Pre-Cata
            (flags, idx_x, idx_y, n_layers, n_doodad_refs, holes,
             layer_alpha_1, area_id, n_sound_emitters, n_sound_emitter_files,
             liquid_level, pred_tex, n_effect_doodad, holes_high,
             offset_mcly, offset_mcrf, offset_mcal, size_mcal,
             offset_mcsh, size_mcsh, pad_1, pad_2,
             pad_3, offset_mclv, flags_3,
             offset_mccv, offset_mclq, offset_mcse) = struct.unpack('<IIIIIIIIIIFFIIIIIIIIIIIIIIIII', data[:112])
            
            return cls(
                MCNKFlags(flags), idx_x, idx_y, n_layers, n_doodad_refs,
                holes, layer_alpha_1, area_id, n_sound_emitters,
                n_sound_emitter_files, liquid_level, pred_tex,
                n_effect_doodad, holes_high, offset_mcly, offset_mcrf,
                offset_mcal, size_mcal, offset_mcsh, size_mcsh,
                0, 0, 0, pad_3, offset_mclv, flags_3,
                offset_mccv, offset_mclq, offset_mcse
            )

class MCNKChunk:
    """Main MCNK chunk handler"""
    HEADER_SIZE = 128
    
    def __init__(self, data: bytes, version: int = 8):
        self.header = MCNKHeader.from_bytes(data[:self.HEADER_SIZE], version)
        self.version = version
        self._data = data
        self._subchunks: Dict[str, object] = {}
        
        # Initialize mandatory chunks
        self._init_mandatory_chunks()
        
        # Initialize optional chunks based on flags
        self._init_optional_chunks()

    def _init_mandatory_chunks(self):
        """Initialize mandatory sub-chunks (MCVT, MCNR, MCLY)"""
        # Find MCVT (always first after header)
        mcvt_data = self._find_subchunk(self.HEADER_SIZE, 'MCVT')
        if mcvt_data:
            self._subchunks['MCVT'] = MCVTChunk(mcvt_data)

        # Find MCNR (always after MCVT)
        mcnr_data = self._find_subchunk(self.HEADER_SIZE + 584, 'MCNR')  # 584 = MCVT size (145*4)
        if mcnr_data:
            self._subchunks['MCNR'] = MCNRChunk(mcnr_data)

        # Parse MCLY if present
        if self.header.offset_mcly:
            mcly_data = self._get_chunk_data(self.header.offset_mcly)
            if mcly_data:
                self._subchunks['MCLY'] = MCLYChunk(mcly_data, self.version)

    def _init_optional_chunks(self):
        """Initialize optional sub-chunks based on flags"""
        # Parse MCRF (doodad references) if present
        if self.header.flags & MCNKFlags.HAS_DOODAD_REFS and self.header.offset_mcrf:
            mcrf_data = self._get_chunk_data(self.header.offset_mcrf)
            if mcrf_data:
                self._subchunks['MCRF'] = MCRFChunk(mcrf_data)

        # Parse MCSH (shadows) if present
        if self.header.flags & MCNKFlags.HAS_MCSH and self.header.offset_mcsh:
            mcsh_data = self._get_chunk_data(self.header.offset_mcsh, self.header.size_mcsh)
            if mcsh_data:
                self._subchunks['MCSH'] = MCSHChunk(mcsh_data)

        # Parse MCCV (vertex colors) if present
        if self.header.flags & MCNKFlags.HAS_MCCV and self.header.offset_mccv:
            mccv_data = self._get_chunk_data(self.header.offset_mccv)
            if mccv_data:
                self._subchunks['MCCV'] = MCCVChunk(mccv_data)

        # Parse MCLV (lighting) if present
        if self.header.flags & MCNKFlags.HAS_MCLV and self.header.offset_mclv:
            mclv_data = self._get_chunk_data(self.header.offset_mclv)
            if mclv_data:
                self._subchunks['MCLV'] = MCLVChunk(mclv_data)

        # Parse MCAL (alpha maps) if present
        if self.header.offset_mcal:
            mcal_data = self._get_chunk_data(self.header.offset_mcal, self.header.size_mcal)
            if mcal_data:
                mcly = self._subchunks.get('MCLY')
                self._subchunks['MCAL'] = MCALChunk(mcal_data, mcly)

    def _find_subchunk(self, start_offset: int, magic: str) -> Optional[bytes]:
        """Find and extract subchunk data by magic"""
        magic_bytes = magic.encode('ascii')
        pos = start_offset
        
        while pos + 8 <= len(self._data):
            chunk_magic = self._data[pos:pos+4]
            chunk_size = struct.unpack('<I', self._data[pos+4:pos+8])[0]
            
            if chunk_magic == magic_bytes:
                return self._data[pos+8:pos+8+chunk_size]
            
            pos += 8 + chunk_size
        
        return None

    def _get_chunk_data(self, offset: int, size: Optional[int] = None) -> Optional[bytes]:
        """Get chunk data using stored offset and optional size"""
        if offset >= len(self._data):
            return None
            
        if size is None:
            # Try to find size from next chunk or use remaining data
            next_chunk_pos = len(self._data)
            pos = offset + 8  # Skip current chunk header
            
            while pos + 8 <= len(self._data):
                if self._data[pos:pos+4].isalpha():  # Found next chunk
                    next_chunk_pos = pos
                    break
                pos += 1
            
            size = next_chunk_pos - (offset + 8)
        
        return self._data[offset+8:offset+8+size]

    def get_subchunk(self, name: str) -> Optional[object]:
        """Get parsed subchunk by name"""
        return self._subchunks.get(name)

    @property
    def terrain(self) -> Tuple[Optional[MCVTChunk], Optional[MCNRChunk]]:
        """Get height and normal data"""
        return (
            self._subchunks.get('MCVT'),
            self._subchunks.get('MCNR')
        )

    @property
    def textures(self) -> Tuple[Optional[MCLYChunk], Optional[MCALChunk]]:
        """Get texture layers and alpha maps"""
        return (
            self._subchunks.get('MCLY'),
            self._subchunks.get('MCAL')
        )

    @property
    def lighting(self) -> Tuple[Optional[MCCVChunk], Optional[MCLVChunk], Optional[MCSHChunk]]:
        """Get vertex colors, lighting and shadows"""
        return (
            self._subchunks.get('MCCV'),
            self._subchunks.get('MCLV'),
            self._subchunks.get('MCSH')
        )

def example_usage():
    """Example usage of MCNK chunk parsing"""
    # Create a minimal MCNK chunk with some subchunks
    chunk_data = bytearray()
    
    # Add MCNK header (128 bytes)
    header = bytearray([0] * 128)
    # Set some flags and offsets
    struct.pack_into('<I', header, 0, int(MCNKFlags.HAS_MCSH | MCNKFlags.HAS_MCCV))
    struct.pack_into('<I', header, 0x40, 128 + 8)  # offset_mcly after header
    chunk_data.extend(header)
    
    # Add MCVT chunk (heights)
    chunk_data.extend(b'MCVT')
    chunk_data.extend(struct.pack('<I', 580))  # size (145*4)
    chunk_data.extend(struct.pack('<145f', *([0.0] * 145)))  # height data
    
    # Add MCNR chunk (normals)
    chunk_data.extend(b'MCNR')
    chunk_data.extend(struct.pack('<I', 435))  # size (145*3)
    chunk_data.extend(bytes([127] * 435))  # normal data
    
    # Add MCLY chunk (texture layers)
    chunk_data.extend(b'MCLY')
    chunk_data.extend(struct.pack('<I', 16))  # size
    chunk_data.extend(struct.pack('<IIII', 0, 0, 0, 0))  # one texture layer
    
    # Parse the chunk
    mcnk = MCNKChunk(chunk_data, version=8)
    
    # Display results
    print("MCNK Header Info:")
    print(f"Flags: {mcnk.header.flags}")
    print(f"Position: ({mcnk.header.idx_x}, {mcnk.header.idx_y})")
    
    # Check terrain data
    heights, normals = mcnk.terrain
    if heights:
        print("\nHeight Data (first 5):")
        print(heights.height_map[:5])
    
    if normals:
        print("\nNormal Data (first 5):")
        print(normals.normals[:5])
    
    # Check texture data
    layers, alphas = mcnk.textures
    if layers:
        print("\nTexture Layers:")
        for i, layer in enumerate(layers.layers):
            print(f"Layer {i}: Texture ID {layer.texture_id}")

if __name__ == "__main__":
    example_usage()
