import struct
import logging
import math
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

def parse_mver(data):
    """Parse MVER (Version) chunk"""
    version = struct.unpack('<I', data[:4])[0]
    logging.info(f"MVER Chunk: Version = {version}")
    return {'version': version}

def parse_mphd(data):
    """
    Parse MPHD (Map Header) chunk
    Reference: https://wowdev.wiki/WDT#MPHD_chunk
    """
    flags = struct.unpack('<I', data[:4])[0]
    flags_decoded = {
        'wdt_has_mwmo': bool(flags & 0x1),
        'use_global_map_obj': bool(flags & 0x2),
        'has_doodad_refs': bool(flags & 0x8),
        'has_terrain': bool(flags & 0x10),
        'has_normal_maps': bool(flags & 0x20),
        'has_vertex_colors': bool(flags & 0x40),
        'has_height_texturing': bool(flags & 0x80),
        'has_water_layers': bool(flags & 0x100)
    }
    logging.info(f"MPHD Chunk: Flags = {flags:#x}")
    for flag_name, flag_value in flags_decoded.items():
        logging.info(f"  {flag_name}: {flag_value}")
    return {'flags': flags, 'decoded_flags': flags_decoded}

def parse_main(data):
    """
    Parse MAIN chunk (Map tile table)
    Reference: https://wowdev.wiki/WDT#MAIN_chunk
    """
    entry_size = 16  # Size of SMAreaInfo entry
    entry_count = len(data) // entry_size
    entries = []
    
    for i in range(entry_count):
        entry_data = data[i * entry_size:(i + 1) * entry_size]
        offset, size, flags, async_id = struct.unpack('<4I', entry_data)
        
        flags_decoded = {
            'has_adt': bool(flags & 0x1),
            'loaded': bool(flags & 0x2),
            'loaded_async': bool(flags & 0x4),
            'has_mccv': bool(flags & 0x8),
            'has_big_alpha': bool(flags & 0x10),
            'has_terrain': bool(flags & 0x20),
            'has_vertex_colors': bool(flags & 0x40)
        }
        
        x = i % 64
        y = i // 64
        
        entry = {
            'offset': offset,
            'size': size,
            'flags': flags,
            'flags_decoded': flags_decoded,
            'async_id': async_id,
            'coordinates': {'x': x, 'y': y}
        }
        entries.append(entry)
        
        if offset > 0:
            logging.info(f"Tile at ({x}, {y}): Offset = {offset}, Size = {size}, Flags = {flags:#x}")
            for flag_name, flag_value in flags_decoded.items():
                if flag_value:
                    logging.info(f"  {flag_name}: {flag_value}")
    
    return {'entries': entries}

def parse_mwmo(data):
    """Parse MWMO (Map WMO Names) chunk"""
    wmo_names = data.split(b'\0')
    names = [name.decode('utf-8', 'replace') for name in wmo_names if name]
    logging.info(f"MWMO Chunk: {len(names)} WMO names")
    for name in names:
        logging.info(f"  WMO: {name}")
    return {'names': names}

def parse_modf(data):
    """
    Parse MODF (Map Object Definition) chunk
    Reference: https://wowdev.wiki/WDT#MODF_chunk
    """
    entry_size = 64
    entry_count = len(data) // entry_size
    entries = []
    
    for i in range(entry_count):
        entry_data = data[i * entry_size:(i + 1) * entry_size]
        name_id, unique_id = struct.unpack('<II', entry_data[:8])
        position = struct.unpack('<3f', entry_data[8:20])
        rotation = struct.unpack('<3f', entry_data[20:32])
        bounds_min = struct.unpack('<3f', entry_data[32:44])
        bounds_max = struct.unpack('<3f', entry_data[44:56])
        flags, doodad_set, name_set, scale = struct.unpack('<HHHH', entry_data[56:64])
        
        entry = {
            'name_id': name_id,
            'unique_id': unique_id,
            'position': {'x': position[0], 'y': position[1], 'z': position[2]},
            'rotation': {'x': rotation[0], 'y': rotation[1], 'z': rotation[2]},
            'bounds': {
                'min': {'x': bounds_min[0], 'y': bounds_min[1], 'z': bounds_min[2]},
                'max': {'x': bounds_max[0], 'y': bounds_max[1], 'z': bounds_max[2]}
            },
            'flags': flags,
            'doodad_set': doodad_set,
            'name_set': name_set,
            'scale': scale / 1024.0  # Convert to float scale
        }
        entries.append(entry)
        
        logging.info(f"MODF Entry {i}:")
        logging.info(f"  Name ID: {name_id}, Unique ID: {unique_id}")
        logging.info(f"  Position: ({position[0]:.2f}, {position[1]:.2f}, {position[2]:.2f})")
        logging.info(f"  Scale: {scale / 1024.0:.2f}")
    
    return {'entries': entries}

def parse_mwid(data):
    """Parse MWID (Map WMO Index) chunk"""
    count = len(data) // 4
    indices = struct.unpack(f'<{count}I', data)
    logging.info(f"MWID Chunk: {len(indices)} WMO indices")
    return {'indices': list(indices)}

def parse_mddf(data):
    """
    Parse MDDF (Map Doodad Definition) chunk
    Reference: https://wowdev.wiki/WDT#MDDF_chunk
    """
    entry_size = 36
    entry_count = len(data) // entry_size
    entries = []
    
    for i in range(entry_count):
        entry_data = data[i * entry_size:(i + 1) * entry_size]
        name_id, unique_id = struct.unpack('<II', entry_data[:8])
        position = struct.unpack('<3f', entry_data[8:20])
        rotation = struct.unpack('<3f', entry_data[20:32])
        scale, flags = struct.unpack('<HH', entry_data[32:36])
        
        entry = {
            'name_id': name_id,
            'unique_id': unique_id,
            'position': {'x': position[0], 'y': position[1], 'z': position[2]},
            'rotation': {'x': rotation[0], 'y': rotation[1], 'z': rotation[2]},
            'scale': scale / 1024.0,  # Convert to float scale
            'flags': flags
        }
        entries.append(entry)
        
        logging.info(f"MDDF Entry {i}:")
        logging.info(f"  Name ID: {name_id}, Unique ID: {unique_id}")
        logging.info(f"  Position: ({position[0]:.2f}, {position[1]:.2f}, {position[2]:.2f})")
        logging.info(f"  Scale: {scale / 1024.0:.2f}")
    
    return {'entries': entries}

def parse_mmdx(data):
    """Parse MMDX (Map M2 Names) chunk"""
    m2_names = data.split(b'\0')
    names = [name.decode('utf-8', 'replace') for name in m2_names if name]
    logging.info(f"MMDX Chunk: {len(names)} M2 names")
    for name in names:
        logging.info(f"  M2: {name}")
    return {'names': names}

def parse_mmid(data):
    """Parse MMID (Map M2 Index) chunk"""
    count = len(data) // 4
    indices = struct.unpack(f'<{count}I', data)
    logging.info(f"MMID Chunk: {len(indices)} M2 indices")
    return {'indices': list(indices)}

def parse_mtex(data):
    """Parse MTEX (Map Textures) chunk"""
    textures = data.split(b'\0')
    names = [tex.decode('utf-8', 'replace') for tex in textures if tex]
    logging.info(f"MTEX Chunk: {len(names)} textures")
    for name in names:
        logging.info(f"  Texture: {name}")
    return {'textures': names}

def parse_mdnm(data):
    """Parse MDNM (Map Doodad Name) chunk"""
    names = data.split(b'\0')
    doodad_names = [name.decode('utf-8', 'replace') for name in names if name]
    logging.info(f"MDNM Chunk: {len(doodad_names)} doodad names")
    for name in doodad_names:
        logging.info(f"  Doodad: {name}")
    return {'names': doodad_names}

def parse_monm(data):
    """Parse MONM (Map Object Name) chunk"""
    names = data.split(b'\0')
    object_names = [name.decode('utf-8', 'replace') for name in names if name]
    logging.info(f"MONM Chunk: {len(object_names)} object names")
    for name in object_names:
        logging.info(f"  Object: {name}")
    return {'names': object_names}

def parse_mcnk(data):
    """Parse MCNK (Map Chunk) chunk with all subchunks"""
    if len(data) < 128:
        logging.warning(f"MCNK chunk too small: {len(data)} bytes")
        return {'error': 'Insufficient data'}
    
    # Parse header
    flags = struct.unpack('<I', data[0:4])[0]
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
    
    # Parse remaining offsets
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
    
    # Parse MCLV offset (vertex lighting) if present in extended header
    try:
        ofs_mclv = struct.unpack('<I', data[128:132])[0]
    except:
        ofs_mclv = 0
    
    # Parse texture and doodad maps
    tex_map_data = data[64:80]  # 16 bytes for 8x8 2-bit values
    doodad_map_data = data[80:96]  # 16 bytes for 8x8 1-bit values
    
    # Parse low quality texture map
    low_quality_texture_map = []
    for row in range(8):
        row_values = []
        for col in range(8):
            byte_idx = (row * 8 + col) // 4
            bit_offset = ((row * 8 + col) % 4) * 2
            value = (tex_map_data[byte_idx] >> bit_offset) & 0x3
            row_values.append(value)
        low_quality_texture_map.append(row_values)
    
    # Parse doodad effect map
    no_effect_doodad = []
    for row in range(8):
        row_values = []
        for col in range(8):
            byte_idx = (row * 8 + col) // 8
            bit_offset = (row * 8 + col) % 8
            value = bool(doodad_map_data[byte_idx] & (1 << bit_offset))
            row_values.append(value)
        no_effect_doodad.append(row_values)
    
    # Parse sound emitters
    ofs_snd_emitters = struct.unpack('<I', data[96:100])[0]
    n_snd_emitters = struct.unpack('<I', data[100:104])[0]
    ofs_liquid = struct.unpack('<I', data[104:108])[0]
    size_liquid = struct.unpack('<I', data[108:112])[0]
    position = struct.unpack('<fff', data[112:124])
    ofs_mccv = struct.unpack('<I', data[124:128])[0]
    
    # Parse MCLY (Material Layer) chunk if present
    layers = []
    if ofs_layer and n_layers > 0:
        try:
            from adt_parser.mcnk_subchunk_decoders import decode_mcly
            layer_size = n_layers * 16
            layer_data = data[ofs_layer:ofs_layer + layer_size]
            mcly_result = decode_mcly(layer_data, 0, layer_size)
            layers = mcly_result["layers"]
        except Exception as e:
            logging.warning(f"Error decoding MCLY chunk: {e}")
            # Fallback to original layer parsing if the enhanced decoder fails
            layer_data = data[ofs_layer:ofs_layer + layer_size]
            for i in range(n_layers):
                base = i * 16
                if base + 16 > len(layer_data):
                    break
                texture_id, flags, alpha_offset, effect_id = struct.unpack('<4I', layer_data[base:base + 16])
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
    
    # Parse MCAL (Alpha Map) chunk if present
    alpha_maps = []
    if ofs_alpha and size_alpha > 0:
        try:
            from adt_parser.mcnk_subchunk_decoders import decode_mcal
            alpha_data = data[ofs_alpha:ofs_alpha + size_alpha]
            alpha_result = decode_mcal(alpha_data, 0, size_alpha, flags)
            alpha_maps = alpha_result["alpha_maps"]
        except Exception as e:
            logging.warning(f"Error decoding MCAL chunk: {e}")
            # Fallback to original alpha map parsing if the enhanced decoder fails
            alpha_data = data[ofs_alpha:ofs_alpha + size_alpha]
            current_pos = 0
            while current_pos < size_alpha:
                if current_pos + 1 > len(alpha_data):
                    break
                command = alpha_data[current_pos]
                is_compressed = bool(command & 0x80)
                count = command & 0x7F
                
                if is_compressed:
                    if current_pos + 2 <= len(alpha_data):
                        value = alpha_data[current_pos + 1]
                        alpha_map = [value] * count
                        current_pos += 2
                    else:
                        break
                else:
                    if current_pos + 1 + count <= len(alpha_data):
                        alpha_map = list(alpha_data[current_pos + 1:current_pos + 1 + count])
                        current_pos += 1 + count
                    else:
                        break
                
                # Convert to 64x64 grid if we have enough data
                if len(alpha_map) >= 4096:
                    grid = []
                    do_not_fix = bool(flags & MCNKFlags.DO_NOT_FIX_ALPHA_MAP)
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
    
    # Parse MCSE (Sound Emitters) chunk if present
    emitters = []
    if ofs_snd_emitters and n_snd_emitters > 0:
        try:
            from adt_parser.mcnk_subchunk_decoders import decode_mcse
            emitter_size = n_snd_emitters * 28
            emitter_data = data[ofs_snd_emitters:ofs_snd_emitters + emitter_size]
            mcse_result = decode_mcse(emitter_data, 0, emitter_size)
            emitters = mcse_result["emitters"]
        except Exception as e:
            logging.warning(f"Error decoding MCSE chunk: {e}")
            # Fallback to original emitter parsing if the enhanced decoder fails
            emitter_data = data[ofs_snd_emitters:ofs_snd_emitters + emitter_size]
            for i in range(n_snd_emitters):
                base = i * 28
                if base + 28 > len(emitter_data):
                    break
                emitter_id, position_x, position_y, position_z, size_min, size_max, flags = struct.unpack('<I6f', emitter_data[base:base + 28])
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
    
    # Parse MCLV (Vertex Lighting) chunk if present
    vertex_lighting = None
    if ofs_mclv > 0 and ofs_mclv + 64 <= len(data):
        try:
            # MCLV contains 4x4 grid of lighting values
            mclv_data = data[ofs_mclv:ofs_mclv + 64]  # 4x4 grid * 4 bytes per value
            lighting_grid = []
            for y in range(4):
                row = []
                for x in range(4):
                    idx = (y * 4 + x) * 4
                    value = struct.unpack('<f', mclv_data[idx:idx + 4])[0]
                    row.append(value)
                lighting_grid.append(row)
            vertex_lighting = {
                'grid': lighting_grid
            }
        except Exception as e:
            logging.warning(f"Error parsing MCLV chunk: {e}")
    
    # Compile all data
    result = {
        'flags': flags,
        'flags_decoded': {
            'has_mcsh': bool(flags & MCNKFlags.HAS_MCSH),
            'impassable': bool(flags & MCNKFlags.IMPASS),
            'river': bool(flags & MCNKFlags.LQ_RIVER),
            'ocean': bool(flags & MCNKFlags.LQ_OCEAN),
            'magma': bool(flags & MCNKFlags.LQ_MAGMA),
            'slime': bool(flags & MCNKFlags.LQ_SLIME),
            'has_vertex_colors': bool(flags & MCNKFlags.HAS_MCCV),
            'high_res_holes': bool(flags & MCNKFlags.HIGH_RES_HOLES),
            'do_not_fix_alpha_map': bool(flags & MCNKFlags.DO_NOT_FIX_ALPHA_MAP)
        },
        'position': {
            'x': idx_x,
            'y': idx_y,
            'world': {'x': position[0], 'y': position[1], 'z': position[2]}
        },
        'layers': {
            'count': n_layers,
            'data': layers
        },
        'alpha_maps': alpha_maps,
        'sound_emitters': {
            'count': n_snd_emitters,
            'data': emitters
        },
        'area_id': area_id,
        'holes': {
            'high_res': holes_high_res,
            'low_res': holes_low_res
        },
        'texture_map': low_quality_texture_map,
        'doodad_map': no_effect_doodad,
        'offsets': {
            'height': ofs_height,
            'normal': ofs_normal,
            'layer': ofs_layer,
            'refs': ofs_refs,
            'alpha': ofs_alpha,
            'shadow': ofs_shadow,
            'liquid': ofs_liquid,
            'vertex_colors': ofs_mccv,
            'vertex_lighting': ofs_mclv
        },
        'sizes': {
            'alpha': size_alpha,
            'shadow': size_shadow,
            'liquid': size_liquid
        },
        'vertex_lighting': vertex_lighting
    }

def parse_mhdr(data):
    """Parse MHDR (Map Header) chunk"""
    if len(data) < 32:
        logging.warning(f"MHDR chunk too small: {len(data)} bytes")
        return {'error': 'Insufficient data'}
    
    offsets = struct.unpack('<8I', data[:32])
    offset_names = ['mmdx', 'mmid', 'mwmo', 'mwid', 'mddf', 'modf', 'mfbo', 'mh2o']
    
    header_data = {}
    for i, name in enumerate(offset_names):
        header_data[name] = offsets[i]
        if offsets[i] > 0:
            logging.info(f"  {name.upper()} offset: {offsets[i]}")
    
    return header_data

def parse_mcin(data):
    """Parse MCIN (Map Chunk Info) chunk"""
    entry_size = 16
    entry_count = len(data) // entry_size
    entries = []
    
    for i in range(entry_count):
        entry_data = data[i * entry_size:(i + 1) * entry_size]
        offset, size, flags, async_id = struct.unpack('<4I', entry_data)
        
        if offset > 0:
            logging.info(f"MCIN Entry {i}: Offset = {offset}, Size = {size}, Flags = {flags:#x}")
            entries.append({
                'offset': offset,
                'size': size,
                'flags': flags,
                'async_id': async_id
            })
    
    return {'entries': entries}

def text_based_visualization(grid):
    """Generate text-based visualization of the ADT grid"""
    visualization = "\n".join(
        "".join("#" if cell == 1 else "." for cell in row)
        for row in grid
    )
    logging.info("Text-based visualization of the ADT grid:")
    logging.info("\n" + visualization)
