"""
Terrain-specific chunk decoders (MCNK and subchunks)
"""

import struct
import math
from typing import Dict, Any, List
from .base_decoder import ChunkDecoder, Vector3D

class MCNKDecoder(ChunkDecoder):
    """MCNK chunk decoder - Map chunk data"""
    def __init__(self):
        super().__init__(b'MCNK')

    def decode(self, data: bytes) -> Dict[str, Any]:
        # Header is 128 bytes
        if len(data) < 128:
            raise ValueError("MCNK chunk too small")
            
        # Parse header with safe unpacking
        header_data = list(struct.unpack("<16I", data[:64]))
        position_data = list(struct.unpack("<IIIIfffII", data[88:88+36]))
        
        # Decode flags bitwise
        flags = header_data[0]
        mcnk_flags = {
            "has_mcsh": bool(flags & 0x1),
            "impassable": bool(flags & 0x2),
            "liquid_river": bool(flags & 0x4),
            "liquid_ocean": bool(flags & 0x8),
            "liquid_magma": bool(flags & 0x10),
            "liquid_slime": bool(flags & 0x20),
            "has_mccv": bool(flags & 0x40),
            "unknown_0x80": bool(flags & 0x80),
            "do_not_fix_alpha_map": bool(flags & 0x8000),
            "high_res_holes": bool(flags & 0x10000)
        }
        
        # Create offsets dictionary
        offsets = {
            'MCVT': header_data[5] if len(header_data) > 5 else 0,
            'MCNR': header_data[6] if len(header_data) > 6 else 0,
            'MCLY': header_data[7] if len(header_data) > 7 else 0,
            'MCAL': header_data[8] if len(header_data) > 8 else 0,
            'MCSH': header_data[10] if len(header_data) > 10 else 0,
            'MCLQ': header_data[14] if len(header_data) > 14 else 0,
            'MCCV': header_data[15] if len(header_data) > 15 else 0,
        }
        
        # Create sizes dictionary
        sizes = {
            'MCVT': 145 * 4,  # Known vertex height size
            'MCNR': 448,      # Known normals size (435 + 13 padding)
            'MCLY': 16,       # Known layer entry size
            'MCAL': header_data[9] if len(header_data) > 9 else 0,
            'MCSH': header_data[11] if len(header_data) > 11 else 0,
            'MCLQ': header_data[15] if len(header_data) > 15 else 0,
        }
        
        # Process subchunks
        sub_chunks = {}
        layer_flags = 0  # For MCAL decoding
        
        for chunk_id, offset in offsets.items():
            if offset == 0:
                continue
                
            chunk_size = sizes.get(chunk_id, 0)
            if offset >= len(data):
                continue
                
            max_size = len(data) - offset
            chunk_size = min(chunk_size, max_size) if chunk_size > 0 else max_size
            
            if chunk_size == 0:
                continue
                
            sub_chunk_data = data[offset:offset + chunk_size]
            
            # Special handling for MCLY and MCAL
            if chunk_id == 'MCLY':
                result = MCLYDecoder().decode(sub_chunk_data)
                sub_chunks[chunk_id] = result
                if result.get('layers'):
                    layer_flags = result['layers'][0].get('flags', 0)
            elif chunk_id == 'MCAL':
                sub_chunks[chunk_id] = MCALDecoder().decode(sub_chunk_data, layer_flags, flags)
            elif chunk_id == 'MCSH':
                sub_chunks[chunk_id] = MCSHDecoder().decode(sub_chunk_data, flags)
            else:
                # Use appropriate decoder
                decoder_class = {
                    'MCVT': MCVTDecoder,
                    'MCNR': MCNRDecoder,
                    'MCLQ': MCLQDecoder,
                    'MCCV': MCCVDecoder
                }.get(chunk_id)
                
                if decoder_class:
                    sub_chunks[chunk_id] = decoder_class().decode(sub_chunk_data)
        
        return {
            'header': {
                'flags': mcnk_flags,
                'index_x': header_data[1],
                'index_y': header_data[2],
                'layers': header_data[3],
                'doodad_refs': header_data[4],
                'area_id': header_data[13],
                'holes': header_data[15],
                'position': {
                    'x': position_data[5],
                    'y': position_data[6],
                    'z': position_data[4]
                }
            },
            'sub_chunks': sub_chunks
        }

class MCVTDecoder(ChunkDecoder):
    """MCVT chunk decoder - Height map vertices"""
    def __init__(self):
        super().__init__(b'MCVT')

    def decode(self, data: bytes) -> Dict[str, Any]:
        heights = []
        pos = 0
        while pos + 4 <= len(data):
            height = struct.unpack('<f', data[pos:pos+4])[0]
            heights.append(height)
            pos += 4
            
        return {
            'heights': heights,
            'grid_size': {
                'base': 9,
                'total': len(heights)
            }
        }

class MCNRDecoder(ChunkDecoder):
    """MCNR chunk decoder - Normal vectors"""
    def __init__(self):
        super().__init__(b'MCNR')

    def decode(self, data: bytes) -> Dict[str, Any]:
        if len(data) < 435:  # 145 normals * 3 bytes
            raise ValueError("MCNR data too small")
            
        normals = []
        for i in range(0, 435, 3):
            # Unpack in X, Z, Y order
            x, z, y = struct.unpack('3b', data[i:i+3])
            
            # Convert to normalized float values
            x_norm = (x - 127) / 127.0
            y_norm = (y - 127) / 127.0
            
            # Recalculate Z to ensure unit vector
            z_norm = max(0, math.sqrt(max(0, 1 - x_norm**2 - y_norm**2)))
            
            normals.append({
                'x': x_norm,
                'y': y_norm,
                'z': z_norm,
                'original': {'x': x, 'y': y, 'z': z}
            })
            
        # Check for padding
        padding = None
        if len(data) >= 448:
            padding = {
                'bytes': list(data[435:448]),
                'hex': data[435:448].hex()
            }
            
        return {
            'normals': normals,
            'padding': padding,
            'total_normals': len(normals)
        }

class MCLYDecoder(ChunkDecoder):
    """MCLY chunk decoder - Texture layer definitions"""
    def __init__(self):
        super().__init__(b'MCLY')

    def decode(self, data: bytes) -> Dict[str, Any]:
        layers = []
        pos = 0
        while pos + 16 <= len(data):
            texture_id, flags, offset_in_mcal, effect_id = struct.unpack('<4I', data[pos:pos+16])
            
            # Decode flags
            flags_decoded = {
                'animation_rotation': flags & 0x7,
                'animation_speed': (flags >> 3) & 0x7,
                'animation_enabled': bool(flags & 0x100),
                'overbright': bool(flags & 0x200),
                'use_alpha_map': bool(flags & 0x400),
                'alpha_map_compressed': bool(flags & 0x800),
                'use_cube_map_reflection': bool(flags & 0x1000)
            }
            
            layers.append({
                'texture_id': texture_id,
                'flags': flags,
                'flags_decoded': flags_decoded,
                'offset_in_mcal': offset_in_mcal,
                'effect_id': effect_id
            })
            pos += 16
            
        return {
            'layers': layers,
            'layer_count': len(layers)
        }

class MCALDecoder(ChunkDecoder):
    """MCAL chunk decoder - Alpha maps"""
    def __init__(self):
        super().__init__(b'MCAL')

    def decode(self, data: bytes, mcly_flags: int = 0, mcnk_flags: int = 0) -> Dict[str, Any]:
        # Determine alpha map mode
        is_compressed = bool(mcly_flags & 0x200)
        do_not_fix_alpha_map = bool(mcnk_flags & 0x8000)
        
        alpha_map = []
        
        if not is_compressed:
            # Uncompressed alpha map
            alpha_map = list(data)
        else:
            # Compressed alpha map
            pos = 0
            while len(alpha_map) < 4096 and pos < len(data):
                control_byte = data[pos]
                is_fill = bool(control_byte & 0x80)
                count = control_byte & 0x7F
                pos += 1
                
                if is_fill:
                    if pos >= len(data):
                        break
                    value = data[pos]
                    alpha_map.extend([value] * count)
                    pos += 1
                else:
                    if pos + count > len(data):
                        break
                    alpha_map.extend(data[pos:pos+count])
                    pos += count
        
        # Handle do_not_fix_alpha_map flag
        if do_not_fix_alpha_map and len(alpha_map) == 4096:
            fixed_map = []
            for y in range(64):
                for x in range(64):
                    if x == 63:
                        fixed_map.append(alpha_map[y * 64 + 62])
                    elif y == 63:
                        fixed_map.append(alpha_map[62 * 64 + x])
                    else:
                        fixed_map.append(alpha_map[y * 64 + x])
            alpha_map = fixed_map
        
        return {
            'alpha_map': alpha_map,
            'mode': {
                'compressed': is_compressed,
                'do_not_fix_alpha_map': do_not_fix_alpha_map
            },
            'size': len(alpha_map)
        }

class MCSHDecoder(ChunkDecoder):
    """MCSH chunk decoder - Shadow map"""
    def __init__(self):
        super().__init__(b'MCSH')

    def decode(self, data: bytes, mcnk_flags: int = 0) -> Dict[str, Any]:
        do_not_fix_alpha_map = bool(mcnk_flags & 0x8000)
        
        # Unpack bit-packed shadow map
        shadow_map = []
        for byte in data:
            shadow_bits = [bool(byte & (1 << j)) for j in range(8)]
            shadow_map.extend(shadow_bits)
        
        # Handle do_not_fix_alpha_map flag
        if do_not_fix_alpha_map and len(shadow_map) == 4096:
            fixed_map = []
            for y in range(64):
                for x in range(64):
                    if x == 63:
                        fixed_map.append(shadow_map[y * 64 + 62])
                    elif y == 63:
                        fixed_map.append(shadow_map[62 * 64 + x])
                    else:
                        fixed_map.append(shadow_map[y * 64 + x])
            shadow_map = fixed_map
        
        return {
            'shadow_map': shadow_map,
            'mode': {
                'do_not_fix_shadow_map': do_not_fix_alpha_map
            },
            'size': len(shadow_map)
        }

class MCLQDecoder(ChunkDecoder):
    """MCLQ chunk decoder - Liquid data"""
    def __init__(self):
        super().__init__(b'MCLQ')

    def decode(self, data: bytes) -> Dict[str, Any]:
        if len(data) < 8:
            return {'heights': []}
            
        min_height, max_height = struct.unpack('<ff', data[0:8])
        
        heights = []
        pos = 8
        while pos + 4 <= len(data):
            height = struct.unpack('<f', data[pos:pos+4])[0]
            heights.append(height)
            pos += 4
            
        return {
            'min_height': min_height,
            'max_height': max_height,
            'heights': heights
        }

class MCCVDecoder(ChunkDecoder):
    """MCCV chunk decoder - Vertex colors"""
    def __init__(self):
        super().__init__(b'MCCV')

    def decode(self, data: bytes) -> Dict[str, Any]:
        colors = []
        pos = 0
        while pos + 4 <= len(data):
            b, g, r, a = struct.unpack('4B', data[pos:pos+4])
            colors.append({
                'r': r,
                'g': g,
                'b': b,
                'a': a
            })
            pos += 4
            
        return {
            'vertex_colors': colors,
            'color_count': len(colors)
        }