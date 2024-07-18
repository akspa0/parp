import logging
from common_helpers import decode_uint8, decode_uint16, decode_uint32, decode_float, decode_cstring, decode_C3Vector, decode_C3Vector_i, decode_RGBA

# Function to reverse chunk IDs
def reverse_chunk_id(chunk_id):
    return chunk_id[::-1]

# Example decoders for WMO chunks

def decode_MOHD(data, offset=0):
    decoded = {}
    decoded['n_materials'], offset = decode_uint32(data, offset)
    decoded['n_groups'], offset = decode_uint32(data, offset)
    decoded['n_portals'], offset = decode_uint32(data, offset)
    decoded['n_lights'], offset = decode_uint32(data, offset)
    decoded['n_models'], offset = decode_uint32(data, offset)
    decoded['n_doodads'], offset = decode_uint32(data, offset)
    decoded['n_sets'], offset = decode_uint32(data, offset)
    decoded['ambient_color'], offset = decode_uint8(data, offset, 4)
    decoded['id'], offset = decode_uint32(data, offset)
    decoded['bounding_box_corner1'], offset = decode_C3Vector(data, offset)
    decoded['bounding_box_corner2'], offset = decode_C3Vector(data, offset)
    decoded['flags'], offset = decode_uint16(data, offset)
    decoded['n_lods'], offset = decode_uint16(data, offset)
    logging.debug(f"MOHD Chunk: {decoded}")
    return decoded, offset

def decode_MOTX(data, offset=0):
    string_table = []
    while offset < len(data):
        string, offset = decode_cstring(data, offset, len(data) - offset)
        string_table.append(string)
    decoded = {'string_table': string_table}
    logging.debug(f"MOTX Chunk: {decoded}")
    return decoded, offset

def decode_MOMT(data, offset=0):
    entries = []
    entry_size = 64
    while offset < len(data):
        entry = {}
        entry['flags'], offset = decode_uint32(data, offset)
        entry['shader'], offset = decode_uint32(data, offset)
        entry['blend_mode'], offset = decode_uint32(data, offset)
        entry['texture1_ofs'], offset = decode_uint32(data, offset)
        entry['emissive_color'], offset = decode_uint8(data, offset, 4)
        entry['sidn_emissive_color'], offset = decode_uint8(data, offset, 4)
        entry['texture2_ofs'], offset = decode_uint32(data, offset)
        entry['diff_color'], offset = decode_uint8(data, offset, 4)
        entry['terrain_type'], offset = decode_uint32(data, offset)
        entry['texture3_ofs'], offset = decode_uint32(data, offset)
        entry['color3'], offset = decode_uint8(data, offset, 4)
        entry['tex3_flags'], offset = decode_uint32(data, offset)
        entry['runtime_data'], offset = decode_uint32(data, offset, 4)
        entries.append(entry)
    decoded = {'materials': entries}
    logging.debug(f"MOMT Chunk: {decoded}")
    return decoded, offset

def decode_MOGN(data, offset=0):
    string_table = []
    while offset < len(data):
        string, offset = decode_cstring(data, offset, len(data) - offset)
        string_table.append(string)
    decoded = {'string_table': string_table}
    logging.debug(f"MOGN Chunk: {decoded}")
    return decoded, offset

def decode_MOGI(data, offset=0):
    entries = []
    entry_size = 32
    while offset < len(data):
        entry = {}
        entry['flags'], offset = decode_uint32(data, offset)
        entry['bounding_box_corner1'], offset = decode_C3Vector(data, offset)
        entry['bounding_box_corner2'], offset = decode_C3Vector(data, offset)
        entry['name_ofs'], offset = decode_uint32(data, offset)
        entries.append(entry)
    decoded = {'group_info': entries}
    logging.debug(f"MOGI Chunk: {decoded}")
    return decoded, offset

def decode_MOSB(data, offset=0):
    skybox, offset = decode_cstring(data, offset, len(data) - offset)
    decoded = {'skybox': skybox}
    logging.debug(f"MOSB Chunk: {decoded}")
    return decoded, offset

def decode_MOPV(data, offset=0):
    portal_vertices = []
    while offset < len(data):
        vertex, offset = decode_C3Vector(data, offset)
        portal_vertices.append(vertex)
    decoded = {'portal_vertices': portal_vertices}
    logging.debug(f"MOPV Chunk: {decoded}")
    return decoded, offset

def decode_MOPT(data, offset=0):
    entries = []
    entry_size = 20
    while offset < len(data):
        entry = {}
        entry['start_vertex'], offset = decode_uint16(data, offset)
        entry['n_vertices'], offset = decode_uint16(data, offset)
        entry['normal'], offset = decode_C3Vector(data, offset)
        entry['unknown'], offset = decode_float(data, offset)
        entries.append(entry)
    decoded = {'portal_info': entries}
    logging.debug(f"MOPT Chunk: {decoded}")
    return decoded, offset

def decode_MOPR(data, offset=0):
    entries = []
    entry_size = 8
    while offset < len(data):
        entry = {}
        entry['portal_index'], offset = decode_uint16(data, offset)
        entry['group_index'], offset = decode_uint16(data, offset)
        entry['side'], offset = decode_int16(data, offset)
        entry['padding'], offset = decode_uint16(data, offset)
        entries.append(entry)
    decoded = {'portal_relations': entries}
    logging.debug(f"MOPR Chunk: {decoded}")
    return decoded, offset

def decode_MOVV(data, offset=0):
    visible_vertices = []
    while offset < len(data):
        vertex, offset = decode_C3Vector(data, offset)
        visible_vertices.append(vertex)
    decoded = {'visible_vertices': visible_vertices}
    logging.debug(f"MOVV Chunk: {decoded}")
    return decoded, offset

def decode_MOVB(data, offset=0):
    entries = []
    entry_size = 4
    while offset < len(data):
        entry = {}
        entry['start_vertex'], offset = decode_uint16(data, offset)
        entry['n_vertices'], offset = decode_uint16(data, offset)
        entries.append(entry)
    decoded = {'visible_batches': entries}
    logging.debug(f"MOVB Chunk: {decoded}")
    return decoded, offset

def decode_MOLT(data, offset=0):
    entries = []
    entry_size = 48
    while offset < len(data):
        entry = {}
        entry['light_type'], offset = decode_uint8(data, offset)
        entry['type'], offset = decode_uint8(data, offset)
        entry['use_attenuation'], offset = decode_uint8(data, offset)
        entry['padding'], offset = decode_uint8(data, offset)
        entry['color'], offset = decode_uint8(data, offset, 4)
        entry['position'], offset = decode_C3Vector(data, offset)
        entry['intensity'], offset = decode_float(data, offset)
        entry['attenuation_start'], offset = decode_float(data, offset)
        entry['attenuation_end'], offset = decode_float(data, offset)
        entry['unknown1'], offset = decode_float(data, offset)
        entry['unknown2'], offset = decode_float(data, offset)
        entry['unknown3'], offset = decode_float(data, offset)
        entry['unknown4'], offset = decode_float(data, offset)
        entries.append(entry)
    decoded = {'lights': entries}
    logging.debug(f"MOLT Chunk: {decoded}")
    return decoded, offset

def decode_MODS(data, offset=0):
    entries = []
    entry_size = 32
    while offset < len(data):
        entry = {}
        entry['name'], offset = decode_cstring(data, offset, 20)
        entry['start_doodad'], offset = decode_uint32(data, offset)
        entry['n_doodads'], offset = decode_uint32(data, offset)
        entry['padding'], offset = decode_uint32(data, offset)
        entries.append(entry)
    decoded = {'doodad_sets': entries}
    logging.debug(f"MODS Chunk: {decoded}")
    return decoded, offset

def decode_MODN(data, offset=0):
    string_table = []
    while offset < len(data):
        string, offset = decode_cstring(data, offset, len(data) - offset)
        string_table.append(string)
    decoded = {'doodad_names': string_table}
    logging.debug(f"MODN Chunk: {decoded}")
    return decoded, offset

def decode_MODD(data, offset=0):
    entries = []
    entry_size = 40
    while offset < len(data):
        entry = {}
        entry['name_ofs'], offset = decode_uint32(data, offset)
        entry['flags'], offset = decode_uint32(data, offset)
        entry['position'], offset = decode_C3Vector(data, offset)
        entry['rotation'], offset = decode_float(data, offset, 4)
        entry['scale'], offset = decode_float(data, offset)
        entry['color'], offset = decode_uint8(data, offset, 4)
        entries.append(entry)
    decoded = {'doodads': entries}
    logging.debug(f"MODD Chunk: {decoded}")
    return decoded, offset

def decode_MFOG(data, offset=0):
    entries = []
    entry_size = 48
    while offset < len(data):
        entry = {}
        entry['flags'], offset = decode_uint32(data, offset)
        entry['position'], offset = decode_C3Vector(data, offset)
        entry['small_radius'], offset = decode_float(data, offset)
        entry['big_radius'], offset = decode_float(data, offset)
        entry['end_dist'], offset = decode_float(data, offset)
        entry['start_factor'], offset = decode_float(data, offset)
        entry['color1'], offset = decode_uint8(data, offset, 4)
        entry['end_dist2'], offset = decode_float(data, offset)
        entry['start_factor2'], offset = decode_float(data, offset)
        entry['color2'], offset = decode_uint8(data, offset, 4)
        entries.append(entry)
    decoded = {'fogs': entries}
    logging.debug(f"MFOG Chunk: {decoded}")
    return decoded, offset

def decode_MCVP(data, offset=0):
    convex_volume_planes = []
    while offset < len(data):
        plane, offset = decode_C3Vector(data, offset)
        convex_volume_planes.append(plane)
    decoded = {'convex_volume_planes': convex_volume_planes}
    logging.debug(f"MCVP Chunk: {decoded}")
    return decoded, offset

def decode_GFID(data, offset=0):
    entries = []
    while offset < len(data):
        entry, offset = decode_uint32(data, offset)
        entries.append(entry)
    decoded = {'group_file_data_ids': entries}
    logging.debug(f"GFID Chunk: {decoded}")
    return decoded, offset

def decode_MOUV(data, offset=0):
    map_object_uv = []
    while offset < len(data):
        uv, offset = decode_C3Vector(data, offset)
        map_object_uv.append(uv)
    decoded = {'map_object_uv': map_object_uv}
    logging.debug(f"MOUV Chunk: {decoded}")
    return decoded, offset

def decode_MOSI(data, offset=0):
    skybox_file_id, offset = decode_uint32(data, offset)
    decoded = {'skybox_file_id': skybox_file_id}
    logging.debug(f"MOSI Chunk: {decoded}")
    return decoded, offset

def decode_MODI(data, offset=0):
    doodad_file_ids = []
    while offset < len(data):
        file_id, offset = decode_uint32(data, offset)
        doodad_file_ids.append(file_id)
    decoded = {'doodad_file_ids': doodad_file_ids}
    logging.debug(f"MODI Chunk: {decoded}")
    return decoded, offset

# Dictionary to map WMO chunk IDs to decoder functions
wmo_chunk_decoders = {
    'MOHD': decode_MOHD,
    'MOTX': decode_MOTX,
    'MOMT': decode_MOMT,
    'MOGN': decode_MOGN,
    'MOGI': decode_MOGI,
    'MOSB': decode_MOSB,
    'MOPV': decode_MOPV,
    'MOPT': decode_MOPT,
    'MOPR': decode_MOPR,
    'MOVV': decode_MOVV,
    'MOVB': decode_MOVB,
    'MOLT': decode_MOLT,
    'MODS': decode_MODS,
    'MODN': decode_MODN,
    'MODD': decode_MODD,
    'MFOG': decode_MFOG,
    'MCVP': decode_MCVP,
    'GFID': decode_GFID,
    'MOUV': decode_MOUV,
    'MOSI': decode_MOSI,
    'MODI': decode_MODI,
}

def decode_chunk(data, offset=0):
    chunk_id = data[offset:offset + 4].decode('utf-8')
    chunk_size = int.from_bytes(data[offset + 4:offset + 8], byteorder='little')
    chunk_data = data[offset + 8:offset + 8 + chunk_size]
    offset += 8 + chunk_size

    decoder = wmo_chunk_decoders.get(chunk_id) or wmo_chunk_decoders.get(reverse_chunk_id(chunk_id))
    if decoder:
        decoded_data, _ = decoder(chunk_data)
        return decoded_data, offset
    else:
        logging.warning(f"No decoder for chunk: {chunk_id}")
        return {'raw_data': chunk_data.hex()}, offset

def parse_wmo(file_path):
    with open(file_path, 'rb') as file:
        data = file.read()

    offset = 0
    parsed_data = []

    while offset < len(data):
        chunk_id = data[offset:offset + 4].decode('utf-8')
        chunk_size = int.from_bytes(data[offset + 4:offset + 8], byteorder='little')
        chunk_data = data[offset + 8:offset + 8 + chunk_size]
        offset += 8 + chunk_size

        parsed_chunk, _ = decode_chunk(data, offset)
        parsed_data.append({
            'id': chunk_id,
            'size': chunk_size,
            'data': parsed_chunk
        })

    return parsed_data
