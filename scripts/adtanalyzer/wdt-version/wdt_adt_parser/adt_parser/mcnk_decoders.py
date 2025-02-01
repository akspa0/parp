from dataclasses import dataclass
from typing import List, Optional, Tuple
import struct
import array
import logging
import zlib
from enum import Flag, auto

@dataclass
class ADTChunkRef:
    """Reference to a chunk within an ADT file"""
    offset: int
    size: int
    magic: str = "MCNK"

class ChunkError(Exception):
    """Exception raised for errors in chunk processing"""
    pass

logger = logging.getLogger(__name__)

class MCNKFlags(Flag):
    HAS_MCSH = auto()          # Has shadows
    IMPASSABLE = auto()        # Impassable terrain
    RIVER = auto()             # River
    OCEAN = auto()             # Ocean
    MAGMA = auto()             # Magma
    SLIME = auto()             # Slime
    HAS_VERTEX_COLORS = auto() # Has vertex colors
    HIGH_RES_HOLES = auto()    # High resolution holes
    DO_NOT_FIX_ALPHA_MAP = auto() # Don't fix alpha map

@dataclass
class MCNKHeader:
    flags: MCNKFlags
    idx_x: int
    idx_y: int
    n_layers: int
    n_doodad_refs: int
    ofs_height: Optional[int]  # Only if not high_res_holes
    ofs_normal: Optional[int]  # Only if not high_res_holes
    holes_high_res: Optional[int]  # Only if high_res_holes
    ofs_layer: int
    ofs_refs: int
    ofs_alpha: int
    size_alpha: int
    ofs_shadow: int
    size_shadow: int
    area_id: int
    n_map_obj_refs: int
    holes_low_res: int
    unknown_but_used: int
    low_quality_texture_map: List[List[int]]  # 8x8 array of 2-bit values
    no_effect_doodad: List[List[bool]]  # 8x8 array of bools
    ofs_snd_emitters: int
    n_snd_emitters: int
    ofs_liquid: int
    size_liquid: int
    position: tuple[float, float, float]
    ofs_mccv: int
    ofs_mclv: int
    unused: int

    @classmethod
    def from_bytes(cls, data: bytes) -> 'MCNKHeader':
        if len(data) < 128:
            raise ChunkError(f"MCNK header too short: {len(data)} bytes")

        flags = MCNKFlags(struct.unpack('<I', data[0:4])[0])
        idx_x = struct.unpack('<I', data[4:8])[0]
        idx_y = struct.unpack('<I', data[8:12])[0]
        n_layers = struct.unpack('<I', data[12:16])[0]
        n_doodad_refs = struct.unpack('<I', data[16:20])[0]

        # Handle high_res_holes flag
        if flags & MCNKFlags.HIGH_RES_HOLES:
            holes_high_res = struct.unpack('<Q', data[20:28])[0]
            ofs_height = None
            ofs_normal = None
        else:
            holes_high_res = None
            ofs_height = struct.unpack('<I', data[20:24])[0]
            ofs_normal = struct.unpack('<I', data[24:28])[0]

        # Remaining offsets and sizes
        ofs_layer = struct.unpack('<I', data[28:32])[0]
        ofs_refs = struct.unpack('<I', data[32:36])[0]
        ofs_alpha = struct.unpack('<I', data[36:40])[0]
        size_alpha = struct.unpack('<I', data[40:44])[0]
        ofs_shadow = struct.unpack('<I', data[44:48])[0]
        size_shadow = struct.unpack('<I', data[48:52])[0]
        area_id = struct.unpack('<I', data[52:56])[0]
        n_map_obj_refs = struct.unpack('<I', data[56:60])[0]
        holes_low_res = struct.unpack('<H', data[60:62])[0]
        unknown_but_used = struct.unpack('<H', data[62:64])[0]

        # Parse texture and doodad maps
        tex_map_data = data[64:80]  # 16 bytes for 8x8 2-bit values
        doodad_map_data = data[80:96]  # 16 bytes for 8x8 1-bit values

        low_quality_texture_map = []
        for row in range(8):
            row_values = []
            for col in range(8):
                byte_idx = (row * 8 + col) // 4
                bit_offset = ((row * 8 + col) % 4) * 2
                value = (tex_map_data[byte_idx] >> bit_offset) & 0x3
                row_values.append(value)
            low_quality_texture_map.append(row_values)

        no_effect_doodad = []
        for row in range(8):
            row_values = []
            for col in range(8):
                byte_idx = (row * 8 + col) // 8
                bit_offset = (row * 8 + col) % 8
                value = bool(doodad_map_data[byte_idx] & (1 << bit_offset))
                row_values.append(value)
            no_effect_doodad.append(row_values)

        # Final fields
        ofs_snd_emitters = struct.unpack('<I', data[96:100])[0]
        n_snd_emitters = struct.unpack('<I', data[100:104])[0]
        ofs_liquid = struct.unpack('<I', data[104:108])[0]
        size_liquid = struct.unpack('<I', data[108:112])[0]
        position = struct.unpack('<fff', data[112:124])
        ofs_mccv = struct.unpack('<I', data[124:128])[0]

        # These might be version dependent
        try:
            ofs_mclv = struct.unpack('<I', data[128:132])[0]
            unused = struct.unpack('<I', data[132:136])[0]
        except:
            ofs_mclv = 0
            unused = 0

        return cls(
            flags=flags,
            idx_x=idx_x,
            idx_y=idx_y,
            n_layers=n_layers,
            n_doodad_refs=n_doodad_refs,
            ofs_height=ofs_height,
            ofs_normal=ofs_normal,
            holes_high_res=holes_high_res,
            ofs_layer=ofs_layer,
            ofs_refs=ofs_refs,
            ofs_alpha=ofs_alpha,
            size_alpha=size_alpha,
            ofs_shadow=ofs_shadow,
            size_shadow=size_shadow,
            area_id=area_id,
            n_map_obj_refs=n_map_obj_refs,
            holes_low_res=holes_low_res,
            unknown_but_used=unknown_but_used,
            low_quality_texture_map=low_quality_texture_map,
            no_effect_doodad=no_effect_doodad,
            ofs_snd_emitters=ofs_snd_emitters,
            n_snd_emitters=n_snd_emitters,
            ofs_liquid=ofs_liquid,
            size_liquid=size_liquid,
            position=position,
            ofs_mccv=ofs_mccv,
            ofs_mclv=ofs_mclv,
            unused=unused
        )

@dataclass
class AlphaMCNKHeader:
    """Alpha version MCNK header (16 bytes)"""
    flags: int
    area_id: int
    n_layers: int
    n_doodad_refs: int

    @classmethod
    def from_bytes(cls, data: bytes) -> 'AlphaMCNKHeader':
        if len(data) < 16:
            raise ChunkError(f"Alpha MCNK header too short: {len(data)} bytes")
        header = struct.unpack('<4I', data[:16])
        return cls(
            flags=header[0],
            area_id=header[1],
            n_layers=header[2],
            n_doodad_refs=header[3]
        )

class MCNKChunk:
    """MCNK chunk decoder"""
    def __init__(self, chunk_ref: ADTChunkRef, data: bytes, is_alpha: bool = False):
        self.ref = chunk_ref
        self.data = data
        self.is_alpha = is_alpha
        self.header = AlphaMCNKHeader.from_bytes(data[:16]) if is_alpha else MCNKHeader.from_bytes(data[:128])
        self._subchunk_cache = {}
        
        # Calculate Alpha format offsets if needed
        if is_alpha:
            self.mcvt_offset = 16
            self.mcly_offset = self.mcvt_offset + (145 * 4)
            self.mcrf_offset = self.mcly_offset + (self.header.n_layers * 8)
            self.mclq_offset = self.mcrf_offset + (self.header.n_doodad_refs * 4)

    def get_subchunk_data(self, offset: int, size: int) -> Optional[bytes]:
        """Get subchunk data using relative offset"""
        if offset == 0 or size == 0:
            return None
        
        # Offset is relative to MCNK start
        abs_offset = self.ref.offset + offset
        return self.data[offset:offset + size]

    def get_height_map(self) -> Optional[array.array]:
        """Get height map data"""
        if self.is_alpha:
            # Alpha format: 145 floats (9x9 + 8x8 grid) starting at offset 16
            height_data = self.get_subchunk_data(self.mcvt_offset, 145 * 4)
            if height_data:
                return array.array('f', height_data)
            return None
        else:
            # Retail format
            if self.header.flags & MCNKFlags.HIGH_RES_HOLES:
                return None
            height_data = self.get_subchunk_data(self.header.ofs_height, 145 * 4)
            if height_data:
                return array.array('f', height_data)
            return None

    def get_layer_info(self) -> List[dict]:
        """Get texture layer information"""
        if self.is_alpha:
            # Alpha format: 8 bytes per layer (texture_id, flags)
            if not hasattr(self.header, 'n_layers'):
                return []
            layers = []
            layer_data = self.get_subchunk_data(self.mcly_offset, self.header.n_layers * 8)
            if layer_data:
                for i in range(self.header.n_layers):
                    offset = i * 8
                    texture_id, flags = struct.unpack('<2I', layer_data[offset:offset + 8])
                    layers.append({
                        'texture_id': texture_id,
                        'flags': flags,
                        'offset_mcal': 0,  # Not present in Alpha
                        'effect_id': 0  # Not present in Alpha
                    })
            return layers
        else:
            # Retail format: 16 bytes per layer
            if self.header.ofs_layer == 0:
                return []
            layers = []
            layer_data = self.get_subchunk_data(self.header.ofs_layer, self.header.n_layers * 16)
            if layer_data:
                for i in range(self.header.n_layers):
                    offset = i * 16
                    layer_info = struct.unpack('<4I', layer_data[offset:offset + 16])
                    layers.append({
                        'texture_id': layer_info[0],
                        'flags': layer_info[1],
                        'offset_mcal': layer_info[2],
                        'effect_id': layer_info[3]
                    })
            return layers

    def get_alpha_map(self) -> Optional[bytes]:
        """Get alpha map data"""
        return self.get_subchunk_data(self.header.ofs_alpha, self.header.size_alpha)

    def get_shadow_map(self) -> Optional[bytes]:
        """Get shadow map data if present"""
        if self.header.flags & MCNKFlags.HAS_MCSH:
            return self.get_subchunk_data(self.header.ofs_shadow, self.header.size_shadow)
        return None

    def get_liquid_data(self) -> Optional[Tuple[int, array.array]]:
        """Get liquid data if present. Returns tuple of (liquid_type, height_values)"""
        if self.is_alpha:
            # Alpha format: Simple liquid data after MCRF
            # Format: 4 bytes liquid type + array of float height values
            liquid_data = self.get_subchunk_data(self.mclq_offset, -1)  # Get all remaining data
            if liquid_data and len(liquid_data) >= 8:
                liquid_type = struct.unpack('<I', liquid_data[:4])[0]
                height_values = array.array('f', liquid_data[4:])
                return (liquid_type, height_values)
            return None
        else:
            # Retail format
            if hasattr(self.header, 'size_liquid') and self.header.size_liquid > 8:
                liquid_data = self.get_subchunk_data(self.header.ofs_liquid, self.header.size_liquid)
                if liquid_data:
                    # Skip 8 byte header in retail format
                    return (0, array.array('f', liquid_data[8:]))
            return None

    def decode_alpha_map(self, alpha_data: bytes) -> List[List[int]]:
        """Decode alpha map data"""
        if not alpha_data:
            return []

        # Check if we need to fix the alpha map
        fix_alpha = not (self.header.flags & MCNKFlags.DO_NOT_FIX_ALPHA_MAP)
        
        # Process based on compression
        if len(alpha_data) >= 4 and alpha_data[0:4] == b'MCAL':
            # Compressed alpha map
            size = struct.unpack('<I', alpha_data[4:8])[0]
            compressed_data = alpha_data[8:]
            try:
                alpha_data = zlib.decompress(compressed_data)
            except zlib.error as e:
                logger.error(f"Failed to decompress alpha map: {e}")
                return []

        # Convert to 2D array
        size = 64 if fix_alpha else 63
        alpha_map = []
        for y in range(size):
            row = []
            for x in range(size):
                idx = y * size + x
                if idx < len(alpha_data):
                    row.append(alpha_data[idx])
                else:
                    row.append(0)
            alpha_map.append(row)

        return alpha_map

