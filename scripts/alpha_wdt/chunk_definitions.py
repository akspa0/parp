import struct
import logging
import math
from adt_parser.mcnk_decoders import MCNKHeader, MCNKFlags, ADTChunkRef
from adt_parser.texture_decoders import TextureManager, TextureDecoder

# Alpha WDT specific parsers
def parse_alpha_mcnk(data):
    """
    Parse Alpha-specific MCNK chunk (Map Chunk)
    Reference: https://wowdev.wiki/Alpha#MCNK
    
    Alpha MCNK has a simplified 16-byte header followed by:
    - MCVT: 145 float values (9x9 + 8x8 grid) for heightmap
    - MCLY: n_layers * 8 bytes for layer info
    - MCRF: n_doodad_refs * 4 bytes for doodad references
    - MCLQ: Liquid data (if present)
    """
    if len(data) < 16:
        logging.warning("Alpha MCNK chunk too small")
        return None
        
    header = struct.unpack('<4I', data[:16])
    flags = header[0]
    area_id = header[1]
    n_layers = header[2]
    n_doodad_refs = header[3]
    
    # Calculate offsets
    mcvt_offset = 16  # Heightmap starts after header
    mcly_offset = mcvt_offset + (145 * 4)  # After heightmap
    mcrf_offset = mcly_offset + (n_layers * 8)  # After layers
    mclq_offset = mcrf_offset + (n_doodad_refs * 4)  # After doodad refs
    
    # Parse heightmap (145 floats)
    heights = None
    if len(data) >= mcvt_offset + (145 * 4):
        heights = array.array('f', data[mcvt_offset:mcvt_offset + (145 * 4)])
    
    # Parse layer info
    layers = []
    if len(data) >= mcly_offset + (n_layers * 8):
        layer_data = data[mcly_offset:mcly_offset + (n_layers * 8)]
        for i in range(n_layers):
            texture_id, layer_flags = struct.unpack('<2I', layer_data[i * 8:(i + 1) * 8])
            layers.append({
                'texture_id': texture_id,
                'flags': layer_flags,
                'effect_id': 0  # Not present in Alpha
            })
    
    # Parse liquid data if present
    liquid_data = None
    if len(data) > mclq_offset:
        # Alpha liquid data format is simpler than retail
        liquid_data = data[mclq_offset:]
    
    return {
        'flags': flags,
        'area_id': area_id,
        'n_layers': n_layers,
        'n_doodad_refs': n_doodad_refs,
        'heights': heights,
        'layers': layers,
        'liquid_data': liquid_data,
        'offsets': {
            'MCVT': mcvt_offset,
            'MCLY': mcly_offset,
            'MCRF': mcrf_offset,
            'MCLQ': mclq_offset if liquid_data else 0
        }
    }

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

def parse_main(data, wdt_file=None):
    """
    Parse MAIN chunk (Map tile table)
    Reference: https://wowdev.wiki/WDT#MAIN_chunk
    
    Args:
        data: Raw chunk data
        wdt_file: Optional WDTFile instance for enhanced parsing
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
        
        # Enhanced parsing if WDTFile is provided
        if wdt_file and offset > 0:
            # Get MCNK data
            for chunk_ref, chunk_data in wdt_file.get_chunks_by_type('MCNK'):
                mcnk_info = wdt_file.parse_mcnk(chunk_ref)
                if mcnk_info.idx_x == x and mcnk_info.idx_y == y:
                    entry['mcnk_data'] = {
                        'flags': int(mcnk_info.flags),
                        'n_layers': mcnk_info.n_layers,
                        'n_doodad_refs': mcnk_info.n_doodad_refs,
                        'offsets': {
                            'mcvt': mcnk_info.mcvt_offset,
                            'mcnr': mcnk_info.mcnr_offset,
                            'mcly': mcnk_info.mcly_offset,
                            'mcrf': mcnk_info.mcrf_offset,
                            'mcal': mcnk_info.mcal_offset,
                            'mcsh': mcnk_info.mcsh_offset,
                            'mclq': mcnk_info.mclq_offset
                        }
                    }
                    
                    # Parse layer data if available
                    if mcnk_info.mcly_data:
                        layers = []
                        layer_data = mcnk_info.mcly_data
                        n_layers = len(layer_data) // 16
                        for layer_idx in range(n_layers):
                            layer_offset = layer_idx * 16
                            texture_id, flags, alpha_offset, effect_id = struct.unpack(
                                '<4I', layer_data[layer_offset:layer_offset + 16]
                            )
                            layers.append({
                                'texture_id': texture_id,
                                'flags': flags,
                                'alpha_offset': alpha_offset,
                                'effect_id': effect_id
                            })
                        entry['mcnk_data']['layers'] = layers
                    break
            
            # Get texture data
            if 'MTEX' in wdt_file.chunk_index:
                for chunk_ref, mtex_data in wdt_file.get_chunks_by_type('MTEX'):
                    mtxf_data = None
                    if 'MTXF' in wdt_file.chunk_index:
                        mtxf_chunks = wdt_file.get_chunks_by_type('MTXF')
                        if mtxf_chunks:
                            _, mtxf_data = mtxf_chunks[0]
                    
                    texture_info = parse_mtex(mtex_data, mtxf_data, mcnk_info.mcly_data if 'mcnk_data' in entry else None)
                    entry['textures'] = texture_info
                    break
        
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

def parse_mtex(data, mtxf_data=None, mcly_data=None):
    """
    Parse MTEX (Map Textures) chunk along with optional MTXF and MCLY data
    Returns enhanced texture information using TextureManager
    """
    # Create texture manager and load all texture data
    manager = TextureManager()
    manager.load_from_chunks(data, mtxf_data, mcly_data)
    
    # Get basic texture list for backward compatibility
    textures = [tex.filename for tex in manager.get_all_textures()]
    
    # Get detailed texture information
    texture_info = []
    for texture in manager.get_all_textures():
        info = {
            'path': texture.filename,
            'id': texture.texture_id,
            'flags': {
                'is_terrain': texture.flags.is_terrain,
                'is_hole': texture.flags.is_hole,
                'is_water': texture.flags.is_water,
                'has_alpha': texture.flags.has_alpha,
                'is_animated': texture.flags.is_animated
            }
        }
        
        # Include layer information if available
        if texture.layers:
            info['layers'] = [{
                'blend_mode': layer.blend_mode,
                'has_alpha_map': layer.has_alpha_map,
                'is_compressed': layer.is_compressed,
                'effect_id': layer.effect_id
            } for layer in texture.layers]
        
        texture_info.append(info)
    
    # Log texture statistics
    stats = manager.analyze_texture_usage()
    logging.info(f"MTEX Chunk: {stats['total']} textures")
    logging.info(f"  Terrain textures: {stats['terrain']}")
    logging.info(f"  Water textures: {stats['water']}")
    logging.info(f"  Animated textures: {stats['animated']}")
    logging.info(f"  Textures with alpha: {stats['with_alpha']}")
    logging.info(f"  Total layers: {stats['layers']}")
    
    return {
        'textures': textures,  # Basic list for backward compatibility
        'texture_info': texture_info,  # Detailed information
        'statistics': stats  # Usage statistics
    }

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
    """Parse MCNK (Map Chunk) chunk"""
    if len(data) < 128:
        logging.warning(f"MCNK chunk too small: {len(data)} bytes")
        return {'error': 'Insufficient data'}
    
    # Parse header using MCNKHeader from mcnk_decoders
    header = MCNKHeader.from_bytes(data[:128])
    
    # Get layer information
    layers = []
    if header.ofs_layer > 0:
        layer_data = data[header.ofs_layer:header.ofs_layer + header.n_layers * 16]
        for i in range(header.n_layers):
            offset = i * 16
            layer_info = struct.unpack('<4I', layer_data[offset:offset + 16])
            layers.append({
                'texture_id': layer_info[0],
                'flags': layer_info[1],
                'offset_mcal': layer_info[2],
                'effect_id': layer_info[3]
            })
    
    # Get alpha maps for each layer
    alpha_maps = []
    for layer in layers:
        if layer['offset_mcal'] > 0:
            alpha_data = data[layer['offset_mcal']:layer['offset_mcal'] + header.size_alpha]
            alpha_maps.append(alpha_data)
        else:
            alpha_maps.append(None)
    
    # Collect all offsets
    offsets = {
        'mcvt': header.ofs_height,
        'mcnr': header.ofs_normal,
        'mcly': header.ofs_layer,
        'mcrf': header.ofs_refs,
        'mcal': header.ofs_alpha,
        'mcsh': header.ofs_shadow,
        'mclq': header.ofs_liquid
    }
    
    return {
        'flags': header.flags,
        'position': {'x': header.idx_x, 'y': header.idx_y},
        'layers': layers,
        'alpha_maps': alpha_maps,
        'doodad_refs': header.n_doodad_refs,
        'offsets': offsets,
        'area_id': header.area_id,
        'holes': header.holes_low_res,
        'liquid': {
            'offset': header.ofs_liquid,
            'size': header.size_liquid
        }
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