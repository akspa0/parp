import struct
import logging
import math

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
    """Parse MCNK (Map Chunk) chunk"""
    if len(data) < 128:
        logging.warning(f"MCNK chunk too small: {len(data)} bytes")
        return {'error': 'Insufficient data'}
    
    flags = struct.unpack('<I', data[0:4])[0]
    idx_x = struct.unpack('<I', data[4:8])[0]
    idx_y = struct.unpack('<I', data[8:12])[0]
    layers = struct.unpack('<I', data[12:16])[0]
    doodad_refs = struct.unpack('<I', data[16:20])[0]
    
    flags_decoded = {
        'has_mcsh': bool(flags & 0x1),
        'impassable': bool(flags & 0x2),
        'river': bool(flags & 0x4),
        'ocean': bool(flags & 0x8),
        'magma': bool(flags & 0x10),
        'slime': bool(flags & 0x20),
        'has_vertex_colors': bool(flags & 0x40)
    }
    
    logging.info(f"MCNK Chunk: Position ({idx_x}, {idx_y})")
    logging.info(f"  Layers: {layers}, Doodad refs: {doodad_refs}")
    for flag_name, flag_value in flags_decoded.items():
        if flag_value:
            logging.info(f"  {flag_name}: {flag_value}")
    
    return {
        'flags': flags_decoded,
        'position': {'x': idx_x, 'y': idx_y},
        'layers': layers,
        'doodad_refs': doodad_refs
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
