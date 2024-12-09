import struct
import re

def write_chunk(chunk_name, chunk_data):
    """Writes a chunk in the format: name + size + data."""
    return chunk_name + struct.pack('<I', len(chunk_data)) + chunk_data

def build_string_block(strings):
    """Builds a null-terminated string block."""
    return b'\0'.join(s.encode('utf-8') for s in strings) + b'\0' if strings else b''

def build_offsets_block(strings_block, strings_list):
    """Builds an offsets block for a string block."""
    offsets = []
    for s in strings_list:
        off = strings_block.find((s + '\0').encode('utf-8'))
        offsets.append(off)
    return struct.pack('<' + 'I' * len(offsets), *offsets)

def build_mmdx_mmid_chunks(m2_names):
    """Builds MMDX and MMID chunks for M2 models."""
    if not m2_names:
        return b'', b''
    mmdx_block = build_string_block(m2_names)
    mmid_data = build_offsets_block(mmdx_block, m2_names)
    return write_chunk(b'MMDX', mmdx_block), write_chunk(b'MMID', mmid_data)

def build_mwmo_mwid_chunks(wmo_names):
    """Builds MWMO and MWID chunks for WMO models."""
    if not wmo_names:
        return b'', b''
    mwmo_block = build_string_block(wmo_names)
    mwid_data = build_offsets_block(mwmo_block, wmo_names)
    return write_chunk(b'MWMO', mwmo_block), write_chunk(b'MWID', mwid_data)

def build_mtex_chunk(textures):
    """Builds an MTEX chunk for valid textures."""
    if not textures:
        return b''
    mtex_block = build_string_block(textures)
    return write_chunk(b'MTEX', mtex_block)

def parse_mddf(data):
    """Parses MDDF (M2 placement) data."""
    entries = []
    for i in range(0, len(data), 36):
        entry = struct.unpack('<IIfff' + 'fff' + 'HH', data[i:i+36])
        entries.append({
            'nameId': entry[0],
            'uniqueId': entry[1],
            'position': entry[2:5],
            'rotation': entry[5:8],
            'scale': entry[8],
            'flags': entry[9]
        })
    return entries

def parse_modf(data):
    """Parses MODF (WMO placement) data."""
    entries = []
    for i in range(0, len(data), 64):
        entry = struct.unpack('<IIfff' + 'fff' + 'fff' + 'fff' + 'HHHH', data[i:i+64])
        entries.append({
            'nameId': entry[0],
            'uniqueId': entry[1],
            'position': entry[2:5],
            'rotation': entry[5:8],
            'extents_lower': entry[8:11],
            'extents_upper': entry[11:14],
            'flags': entry[14],
            'doodadSet': entry[15],
            'nameSet': entry[16],
            'scale': entry[17]
        })
    return entries

def build_mddf_chunk(entries):
    """Builds MDDF chunk for M2 placements."""
    data = b''.join(
        struct.pack('<IIfff' + 'fff' + 'HH',
                    e['nameId'], e['uniqueId'],
                    *e['position'], *e['rotation'],
                    e['scale'], e['flags']) for e in entries
    )
    return write_chunk(b'MDDF', data)

def build_modf_chunk(entries):
    """Builds MODF chunk for WMO placements."""
    data = b''.join(
        struct.pack('<IIfff' + 'fff' + 'fff' + 'fff' + 'HHHH',
                    e['nameId'], e['uniqueId'],
                    *e['position'], *e['rotation'],
                    *e['extents_lower'], *e['extents_upper'],
                    e['flags'], e['doodadSet'], e['nameSet'], e['scale']) for e in entries
    )
    return write_chunk(b'MODF', data)

def normalize_filename(fname):
    """Normalizes filenames for consistent comparison."""
    if not fname or fname == "<invalid offset>":
        return ""
    fname_norm = fname.lower().replace('\\', '/')
    fname_norm = fname_norm.lstrip('./').lstrip('/')
    fname_norm = re.sub('/+', '/', fname_norm)
    if fname_norm.endswith('.mdx'):
        fname_norm = fname_norm[:-4] + '.m2'
    return fname_norm

def rebuild_chunks(valid_m2, valid_wmo, valid_textures, mddf_entries, modf_entries, orig_m2, orig_wmo):
    """
    Rebuilds all model-related and texture-related chunks.
    """
    # Normalize names for mapping
    valid_m2_norm = [normalize_filename(m) for m in valid_m2]
    valid_wmo_norm = [normalize_filename(w) for w in valid_wmo]

    # Remap nameIds for M2
    final_m2_list = [name for i, name in enumerate(orig_m2) if normalize_filename(name) in valid_m2_norm]
    m2_name_map = {normalize_filename(name): i for i, name in enumerate(final_m2_list)}
    new_mddf = [
        {**e, 'nameId': m2_name_map[normalize_filename(orig_m2[e['nameId']])]} 
        for e in mddf_entries 
        if e['nameId'] < len(orig_m2) and normalize_filename(orig_m2[e['nameId']]) in valid_m2_norm
    ]

    # Remap nameIds for WMO
    final_wmo_list = [name for i, name in enumerate(orig_wmo) if normalize_filename(name) in valid_wmo_norm]
    wmo_name_map = {normalize_filename(name): i for i, name in enumerate(final_wmo_list)}
    new_modf = [
        {**e, 'nameId': wmo_name_map[normalize_filename(orig_wmo[e['nameId']])]} 
        for e in modf_entries 
        if e['nameId'] < len(orig_wmo) and normalize_filename(orig_wmo[e['nameId']]) in valid_wmo_norm
    ]

    # Rebuild chunks
    mmdx_chunk, mmid_chunk = build_mmdx_mmid_chunks(final_m2_list)
    mwmo_chunk, mwid_chunk = build_mwmo_mwid_chunks(final_wmo_list)
    mtex_chunk = build_mtex_chunk(valid_textures)

    return {
        'MMDX': mmdx_chunk,
        'MMID': mmid_chunk,
        'MWMO': mwmo_chunk,
        'MWID': mwid_chunk,
        'MTEX': mtex_chunk,
        'MDDF': build_mddf_chunk(new_mddf),
        'MODF': build_modf_chunk(new_modf),
    }
