from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any
import struct
from enum import IntFlag

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

def decode_mcvt(data: bytes, offset: int, size: int) -> Dict[str, Any]:
    """Decode MCVT (height vertices) chunk"""
    vertices = []
    num_vertices = 145  # 9x9 + 8x8
    
    try:
        for i in range(num_vertices):
            if offset + (i+1)*4 > len(data):
                break
            height = struct.unpack_from('<f', data, offset + i*4)[0]
            vertices.append(height)
        
        return {
            'heights': vertices,
            'grid_size': '9x9 + 8x8',
            'vertex_count': len(vertices)
        }
    except Exception as e:
        return {
            'error': str(e),
            'raw_data': data[offset:offset+size].hex()
        }

def decode_mcnr(data: bytes, offset: int, size: int) -> Dict[str, Any]:
    """Decode MCNR (normals) chunk"""
    normals = []
    num_vertices = 145  # 9x9 + 8x8
    
    try:
        for i in range(num_vertices):
            base = offset + i*3
            if base + 3 > len(data):
                break
            # Each normal is 3 signed bytes (-127 to 127)
            x = int.from_bytes(data[base:base+1], byteorder='little', signed=True) / 127
            y = int.from_bytes(data[base+1:base+2], byteorder='little', signed=True) / 127
            z = int.from_bytes(data[base+2:base+3], byteorder='little', signed=True) / 127
            normals.append([x, y, z])
        
        return {
            'normals': normals,
            'grid_size': '9x9 + 8x8',
            'normal_count': len(normals)
        }
    except Exception as e:
        return {
            'error': str(e),
            'raw_data': data[offset:offset+size].hex()
        }

def decode_mcsh(data: bytes, offset: int, size: int) -> Dict[str, Any]:
    """Decode MCSH (shadow map) chunk"""
    try:
        shadow_map = []
        for i in range(64):  # 8x8 cells, each with a shadow value
            if offset + i >= len(data):
                break
            value = data[offset + i]
            shadow_map.append(value)
        
        return {
            'shadow_map': shadow_map,
            'grid_size': '8x8',
            'cell_count': len(shadow_map)
        }
    except Exception as e:
        return {
            'error': str(e),
            'raw_data': data[offset:offset+size].hex()
        }

def decode_mccv(data: bytes, offset: int, size: int) -> Dict[str, Any]:
    """Decode MCCV (vertex colors) chunk"""
    colors = []
    num_vertices = 145  # 9x9 + 8x8
    
    try:
        for i in range(num_vertices):
            base = offset + i*4
            if base + 4 > len(data):
                break
            b, g, r, a = struct.unpack_from('<4B', data, base)
            colors.append({
                'r': r,
                'g': g,
                'b': b,
                'a': a
            })
        
        return {
            'colors': colors,
            'grid_size': '9x9 + 8x8',
            'vertex_count': len(colors)
        }
    except Exception as e:
        return {
            'error': str(e),
            'raw_data': data[offset:offset+size].hex()
        }

def decode_mclv(data: bytes, offset: int, size: int) -> Dict[str, Any]:
    """Decode MCLV (light values) chunk"""
    light_values = []
    num_vertices = 145  # 9x9 + 8x8
    
    try:
        for i in range(num_vertices):
            base = offset + i*2
            if base + 2 > len(data):
                break
            value = struct.unpack_from('<H', data, base)[0]
            light_values.append(value)
        
        return {
            'light_values': light_values,
            'grid_size': '9x9 + 8x8',
            'vertex_count': len(light_values)
        }
    except Exception as e:
        return {
            'error': str(e),
            'raw_data': data[offset:offset+size].hex()
        }

def decode_mcrf(data: bytes, offset: int, size: int) -> Dict[str, Any]:
    """Decode MCRF (doodad references) chunk"""
    try:
        refs = []
        num_refs = size // 4  # Each reference is a uint32
        
        for i in range(num_refs):
            if offset + (i+1)*4 > len(data):
                break
            ref = struct.unpack_from('<I', data, offset + i*4)[0]
            refs.append(ref)
        
        return {
            'doodad_refs': refs,
            'ref_count': len(refs)
        }
    except Exception as e:
        return {
            'error': str(e),
            'raw_data': data[offset:offset+size].hex()
        }

def decode_mcly(data: bytes, offset: int, size: int) -> Dict[str, Any]:
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

def decode_mcal(data: bytes, offset: int, size: int, mcnk_flags: int = 0) -> Dict[str, Any]:
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
class MCNKChunk:
    """MCNK chunk decoder"""
    def __init__(self, data: bytes):
        self.data = data
        self.header = MCNKHeader.from_bytes(data[:128])
        self._decode_subchunks()

    def _decode_subchunks(self):
        """Decode all subchunks"""
        self.mcvt = None  # Height data
        self.mcnr = None  # Normals
        self.mcly = None  # Layers
        self.mcrf = None  # Doodad references
        self.mcal = None  # Alpha maps
        self.mcsh = None  # Shadows
        self.mccv = None  # Vertex colors
        self.mclv = None  # Light values
        
        # Decode height vertices (MCVT)
        if self.header.ofs_height:
            self.mcvt = decode_mcvt(
                self.data[self.header.ofs_height:],
                0,
                9*9*4 + 8*8*4  # 145 vertices total
            )
        
        # Decode normals (MCNR)
        if self.header.ofs_normal:
            self.mcnr = decode_mcnr(
                self.data[self.header.ofs_normal:],
                0,
                9*9*3 + 8*8*3  # 145 normals * 3 bytes each
            )
        
        # Decode layers (MCLY)
        if self.header.ofs_layer and self.header.n_layers > 0:
            layer_size = self.header.n_layers * 16
            self.mcly = decode_mcly(
                self.data[self.header.ofs_layer:], 
                0, 
                layer_size
            )
        
        # Decode doodad references (MCRF)
        if self.header.ofs_refs and self.header.n_doodad_refs > 0:
            self.mcrf = decode_mcrf(
                self.data[self.header.ofs_refs:],
                0,
                self.header.n_doodad_refs * 4
            )
        
        # Decode alpha maps (MCAL)
        if self.header.ofs_alpha and self.header.size_alpha > 0:
            self.mcal = decode_mcal(
                self.data[self.header.ofs_alpha:],
                0,
                self.header.size_alpha,
                self.header.flags
            )
        
        # Decode shadows (MCSH)
        if self.header.ofs_shadow and self.header.size_shadow > 0:
            self.mcsh = decode_mcsh(
                self.data[self.header.ofs_shadow:],
                0,
                self.header.size_shadow
            )
        
        # Decode vertex colors (MCCV)
        if self.header.ofs_mccv:
            self.mccv = decode_mccv(
                self.data[self.header.ofs_mccv:],
                0,
                145 * 4  # 145 vertices * 4 bytes (BGRA)
            )
        
        # Decode light values (MCLV)
        if self.header.ofs_mclv:
            self.mclv = decode_mclv(
                self.data[self.header.ofs_mclv:],
                0,
                145 * 2  # 145 vertices * 2 bytes
            )

    def to_dict(self) -> Dict[str, Any]:
        """Returns dictionary representation of the chunk"""
        return {
            'mcvt': self.mcvt,
            'mcnr': self.mcnr,
            'mcly': self.mcly,
            'mcrf': self.mcrf,
            'mcal': self.mcal,
            'mcsh': self.mcsh,
            'mccv': self.mccv,
            'mclv': self.mclv
        }

class ChunkError(Exception):
    """Exception raised for errors in chunk processing"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
