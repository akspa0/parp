from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import struct
from enum import IntFlag
import numpy as np
import zlib

class MCLYFlags(IntFlag):
    """MCLY chunk flags"""
    ANIMATION_ROTATION = 0x7       # 3 bits - each tick is 45°
    ANIMATION_SPEED = 0x38        # 3 bits (shifted by 3)
    ANIMATION_ENABLED = 0x40      # 1 bit
    OVERBRIGHT = 0x80            # Makes texture brighter (used for lava)
    USE_ALPHA_MAP = 0x100        # Set for every layer after first
    ALPHA_COMPRESSED = 0x200     # Indicates compressed alpha map
    USE_CUBE_MAP_REFLECTION = 0x400  # Makes layer reflect skybox
    UNKNOWN_800 = 0x800          # WoD+ texture scale related
    UNKNOWN_1000 = 0x1000        # WoD+ texture scale related

class MCNKFlags(IntFlag):
    """MCNK chunk flags"""
    HAS_MCSH = 0x1
    IMPASS = 0x2
    LQ_RIVER = 0x4
    LQ_OCEAN = 0x8
    LQ_MAGMA = 0x10
    LQ_SLIME = 0x20
    HAS_MCCV = 0x40
    UNKNOWN_0X80 = 0x80
    HIGH_RES_HOLES = 0x8000
    DO_NOT_FIX_ALPHA_MAP = 0x10000

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

def decode_mcly(data: bytes, offset: int, size: int) -> Dict:
    """Decode MCLY (Material Layer) chunk"""
    layers = []
    n_layers = size // 16  # Each layer entry is 16 bytes

    for i in range(n_layers):
        base = offset + (i * 16)
        if base + 16 > len(data):
            break

        texture_id, flags, alpha_offset, effect_id = struct.unpack_from('<4I', data, base)
        
        layer = {
            "textureId": texture_id,
            "flags": {
                "raw_value": flags,
                "animation_rotation": flags & 0x7,
                "animation_speed": (flags >> 3) & 0x7,
                "animation_enabled": bool(flags & 0x40),
                "overbright": bool(flags & 0x80),
                "use_alpha_map": bool(flags & 0x100),
                "alpha_compressed": bool(flags & 0x200),
                "use_cube_map_reflection": bool(flags & 0x400),
                "unknown_0x800": bool(flags & 0x800),
                "unknown_0x1000": bool(flags & 0x1000)
            },
            "alpha_map_offset": alpha_offset,
            "effect_id": effect_id
        }
        layers.append(layer)

    return {"layers": layers}

def decode_mcal(data: bytes, offset: int, size: int, mcnk_flags: int = 0) -> Dict:
    """Decode MCAL (Alpha Map) chunk"""
    do_not_fix = bool(mcnk_flags & MCNKFlags.DO_NOT_FIX_ALPHA_MAP)
    alpha_maps = []
    
    if size == 0:
        return {"alpha_maps": alpha_maps}

    current_pos = offset
    while current_pos < offset + size:
        # Check for compression header
        if current_pos + 1 <= len(data):
            command = data[current_pos]
            is_compressed = bool(command & 0x80)
            count = command & 0x7F
            
            if is_compressed:
                # Compressed format
                if current_pos + 2 <= len(data):
                    value = data[current_pos + 1]
                    alpha_map = [value] * count
                    current_pos += 2
                else:
                    break
            else:
                # Uncompressed format
                if current_pos + 1 + count <= len(data):
                    alpha_map = list(data[current_pos + 1:current_pos + 1 + count])
                    current_pos += 1 + count
                else:
                    break

            # Convert to 64x64 grid if we have enough data
            if len(alpha_map) >= 4096:
                grid = []
                for y in range(64 if not do_not_fix else 63):
                    row = []
                    for x in range(64 if not do_not_fix else 63):
                        idx = y * 64 + x
                        if idx < len(alpha_map):
                            row.append(alpha_map[idx])
                        else:
                            row.append(0)
                    if do_not_fix:
                        row.append(row[-1])  # Duplicate last value
                    grid.append(row)
                
                if do_not_fix:
                    grid.append(grid[-1][:])  # Duplicate last row

                alpha_maps.append({
                    "format": "compressed" if is_compressed else "uncompressed",
                    "data": grid,
                    "compressed": is_compressed
                })

    return {"alpha_maps": alpha_maps}

def decode_mcse(data: bytes, offset: int, size: int) -> Dict:
    """
    Decode MCSE (Sound Emitters) chunk
    Reference: https://wowdev.wiki/ADT/v18#MCSE_chunk
    """
    emitters = []
    entry_size = 28  # Each sound emitter entry is 28 bytes

    for i in range(size // entry_size):
        base = offset + (i * entry_size)
        if base + entry_size > len(data):
            break

        # Unpack emitter data
        emitter_data = data[base:base + entry_size]
        emitter_id, position_x, position_y, position_z, size_min, size_max, flags = struct.unpack('<I6f', emitter_data)
        
        emitter = {
            "emitter_id": emitter_id,
            "position": {
                "x": position_x,
                "y": position_y,
                "z": position_z
            },
            "size": {
                "min": size_min,
                "max": size_max
            },
            "flags": flags
        }
        emitters.append(emitter)

    return {"emitters": emitters}

class MCNKChunk:
    """MCNK chunk decoder"""
    def __init__(self, data: bytes):
        self.data = data
        self.header = MCNKHeader.from_bytes(data[:128])
        self._decode_subchunks()

    def _decode_subchunks(self):
        """Decode all subchunks"""
        self.mcly = None
        self.mcal = None
        self.mcse = None
        
        if self.header.ofs_layer and self.header.n_layers > 0:
            layer_size = self.header.n_layers * 16
            self.mcly = decode_mcly(
                self.data[self.header.ofs_layer:], 
                0, 
                layer_size
            )
        
        if self.header.ofs_alpha and self.header.size_alpha > 0:
            self.mcal = decode_mcal(
                self.data[self.header.ofs_alpha:],
                0,
                self.header.size_alpha,
                self.header.flags
            )
            
        if self.header.ofs_snd_emitters and self.header.n_snd_emitters > 0:
            emitter_size = self.header.n_snd_emitters * 28
            self.mcse = decode_mcse(
                self.data[self.header.ofs_snd_emitters:],
                0,
                emitter_size
            )

    def get_layers(self) -> List[Dict]:
        """Get decoded layer information"""
        return self.mcly["layers"] if self.mcly else []

    def get_alpha_maps(self) -> List[Dict]:
        """Get decoded alpha maps"""
        return self.mcal["alpha_maps"] if self.mcal else []
        
    def get_sound_emitters(self) -> List[Dict]:
        """Get decoded sound emitters"""
        return self.mcse["emitters"] if self.mcse else []
