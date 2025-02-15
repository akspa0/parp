"""MCNK (Map Chunk) header."""
from dataclasses import dataclass
from enum import IntFlag
import struct
from typing import Optional, List, Tuple

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
class McnkHeader:
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
    pred_tex: float          # Index for tex coords prediction
    n_effect_doodad: int     # BFA+: unused
    holes_high: int          # Legion+: Additional holes mask
    offset_mcly: int         # MCLY offset (relative to chunk start)
    offset_mcrf: int         # MCRF offset
    offset_mcal: int         # MCAL offset
    size_mcal: int           # MCAL size
    offset_mcsh: int         # MCSH offset
    size_mcsh: int           # MCSH size
    area_id_2: int          # BFA+: area ID (previously padding)
    offset_mcal_2: int      # BFA+: MCAL offset (prev padding)
    flags_2: int            # BFA+: additional flags
    pad_3: int
    offset_mclv: int        # MCLV offset
    flags_3: int            # Counter for BFA+ alpha
    offset_mccv: int        # MCCV offset
    position: Tuple[float, float, float]  # XYZ position

    @classmethod
    def from_bytes(cls, data: bytes) -> 'McnkHeader':
        """Create header from bytes.
        
        Args:
            data: Raw header data (128 bytes)
            
        Returns:
            Parsed header object
        """
        if len(data) < 128:
            raise ValueError(f"MCNK header too short: {len(data)} bytes")

        # Parse fields individually to avoid struct format issues
        flags = MCNKFlags(struct.unpack('<I', data[0:4])[0])
        idx_x = struct.unpack('<I', data[4:8])[0]
        idx_y = struct.unpack('<I', data[8:12])[0]
        n_layers = struct.unpack('<I', data[12:16])[0]
        n_doodad_refs = struct.unpack('<I', data[16:20])[0]
        holes = struct.unpack('<I', data[20:24])[0]
        layer_alpha_1 = struct.unpack('<I', data[24:28])[0]
        area_id = struct.unpack('<I', data[28:32])[0]
        n_sound_emitters = struct.unpack('<I', data[32:36])[0]
        n_sound_emitter_files = struct.unpack('<I', data[36:40])[0]
        liquid_level = struct.unpack('<f', data[40:44])[0]
        pred_tex = struct.unpack('<f', data[44:48])[0]
        n_effect_doodad = struct.unpack('<I', data[48:52])[0]
        holes_high = struct.unpack('<I', data[52:56])[0]
        offset_mcly = struct.unpack('<I', data[56:60])[0]
        offset_mcrf = struct.unpack('<I', data[60:64])[0]
        offset_mcal = struct.unpack('<I', data[64:68])[0]
        size_mcal = struct.unpack('<I', data[68:72])[0]
        offset_mcsh = struct.unpack('<I', data[72:76])[0]
        size_mcsh = struct.unpack('<I', data[76:80])[0]
        area_id_2 = struct.unpack('<I', data[80:84])[0]
        offset_mcal_2 = struct.unpack('<I', data[84:88])[0]
        flags_2 = struct.unpack('<I', data[88:92])[0]
        pad_3 = struct.unpack('<I', data[92:96])[0]
        offset_mclv = struct.unpack('<I', data[96:100])[0]
        flags_3 = struct.unpack('<I', data[100:104])[0]
        offset_mccv = struct.unpack('<I', data[104:108])[0]
        position = struct.unpack('<fff', data[108:120])

        return cls(
            flags=flags,
            idx_x=idx_x,
            idx_y=idx_y,
            n_layers=n_layers,
            n_doodad_refs=n_doodad_refs,
            holes=holes,
            layer_alpha_1=layer_alpha_1,
            area_id=area_id,
            n_sound_emitters=n_sound_emitters,
            n_sound_emitter_files=n_sound_emitter_files,
            liquid_level=liquid_level,
            pred_tex=pred_tex,
            n_effect_doodad=n_effect_doodad,
            holes_high=holes_high,
            offset_mcly=offset_mcly,
            offset_mcrf=offset_mcrf,
            offset_mcal=offset_mcal,
            size_mcal=size_mcal,
            offset_mcsh=offset_mcsh,
            size_mcsh=size_mcsh,
            area_id_2=area_id_2,
            offset_mcal_2=offset_mcal_2,
            flags_2=flags_2,
            pad_3=pad_3,
            offset_mclv=offset_mclv,
            flags_3=flags_3,
            offset_mccv=offset_mccv,
            position=position
        )
