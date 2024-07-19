import logging
from common_helpers import decode_uint8, decode_uint16, decode_uint32, decode_float, decode_cstring, decode_C3Vector, decode_RGBA

def reverse_chunk_id(chunk_id):
    return chunk_id[::-1]

def decode_MOHD(data, offset=0):
    try:
        decoded = {}
        decoded['n_materials'], offset = decode_uint32(data, offset)
        decoded['n_groups'], offset = decode_uint32(data, offset)
        decoded['n_portals'], offset = decode_uint32(data, offset)
        decoded['n_lights'], offset = decode_uint32(data, offset)
        decoded['n_models'], offset = decode_uint32(data, offset)
        decoded['n_doodads'], offset = decode_uint32(data, offset)
        decoded['n_sets'], offset = decode_uint32(data, offset)
        decoded['ambient_color'], offset = decode_uint32(data, offset)
        decoded['id'], offset = decode_uint32(data, offset)
        decoded['bounding_box_corner1'], offset = decode_C3Vector(data, offset)
        decoded['bounding_box_corner2'], offset = decode_C3Vector(data, offset)
        decoded['flags'], offset = decode_uint32(data, offset)
        decoded['n_lods'], offset = decode_uint32(data, offset)
        logging.debug(f"MOHD Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MOHD chunk: {e}")
        return None, offset

def decode_MOTX(data, offset=0):
    try:
        string_table = []
        while offset < len(data):
            string, offset = decode_cstring(data, offset, len(data) - offset)
            string_table.append(string)
        decoded = {'string_table': string_table}
        logging.debug(f"MOTX Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MOTX chunk: {e}")
        return None, offset

def decode_MOMT(data, offset=0):
    try:
        entries = []
        entry_size = 64  # Assuming each MOMT entry is 64 bytes
        while offset + entry_size <= len(data):
            entry = {}
            entry['flags'], offset = decode_uint32(data, offset)
            entry['shader'], offset = decode_uint32(data, offset)
            entry['blend_mode'], offset = decode_uint32(data, offset)
            entry['texture1_ofs'], offset = decode_uint32(data, offset)
            entry['emissive_color'], offset = decode_RGBA(data, offset)
            entry['sidn_emissive_color'], offset = decode_RGBA(data, offset)
            entry['texture2_ofs'], offset = decode_uint32(data, offset)
            entry['diff_color'], offset = decode_RGBA(data, offset)
            entry['terrain_type'], offset = decode_uint32(data, offset)
            entry['texture3_ofs'], offset = decode_uint32(data, offset)
            entry['color3'], offset = decode_RGBA(data, offset)
            entry['tex3_flags'], offset = decode_uint32(data, offset)
            entry['runtime_data'], offset = decode_uint32(data, offset)
            entries.append(entry)
        decoded = {'materials': entries}
        logging.debug(f"MOMT Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MOMT chunk: {e}")
        return None, offset

def decode_MOGN(data, offset=0):
    try:
        string_table = []
        while offset < len(data):
            string, offset = decode_cstring(data, offset, len(data) - offset)
            string_table.append(string)
        decoded = {'string_table': string_table}
        logging.debug(f"MOGN Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MOGN chunk: {e}")
        return None, offset

def decode_MOGI(data, offset=0):
    try:
        entries = []
        entry_size = 32  # Assuming each MOGI entry is 32 bytes
        while offset + entry_size <= len(data):
            entry = {}
            entry['flags'], offset = decode_uint32(data, offset)
            entry['bounding_box_corner1'], offset = decode_C3Vector(data, offset)
            entry['bounding_box_corner2'], offset = decode_C3Vector(data, offset)
            entry['name_ofs'], offset = decode_uint32(data, offset)
            entries.append(entry)
        decoded = {'group_info': entries}
        logging.debug(f"MOGI Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MOGI chunk: {e}")
        return None, offset

def decode_MOSB(data, offset=0):
    try:
        skybox, offset = decode_cstring(data, offset, len(data) - offset)
        decoded = {'skybox': skybox}
        logging.debug(f"MOSB Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MOSB chunk: {e}")
        return None, offset

def decode_MOPV(data, offset=0):
    try:
        portal_vertices = []
        while offset < len(data):
            vertex, offset = decode_C3Vector(data, offset)
            portal_vertices.append(vertex)
        decoded = {'portal_vertices': portal_vertices}
        logging.debug(f"MOPV Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MOPV chunk: {e}")
        return None, offset

def decode_MOPT(data, offset=0):
    try:
        portal_info = []
        while offset < len(data):
            info, offset = decode_uint32(data, offset)
            portal_info.append(info)
        decoded = {'portal_info': portal_info}
        logging.debug(f"MOPT Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MOPT chunk: {e}")
        return None, offset

def decode_MOPR(data, offset=0):
    try:
        portal_relations = []
        while offset < len(data):
            relation, offset = decode_uint32(data, offset)
            portal_relations.append(relation)
        decoded = {'portal_relations': portal_relations}
        logging.debug(f"MOPR Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MOPR chunk: {e}")
        return None, offset

def decode_MOVV(data, offset=0):
    try:
        visible_vertices = []
        while offset < len(data):
            vertex, offset = decode_uint16(data, offset)
            visible_vertices.append(vertex)
        decoded = {'visible_vertices': visible_vertices}
        logging.debug(f"MOVV Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MOVV chunk: {e}")
        return None, offset

def decode_MOVB(data, offset=0):
    try:
        visible_batches = []
        while offset < len(data):
            batch, offset = decode_uint16(data, offset)
            visible_batches.append(batch)
        decoded = {'visible_batches': visible_batches}
        logging.debug(f"MOVB Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MOVB chunk: {e}")
        return None, offset

def decode_MOLT(data, offset=0):
    try:
        lights = []
        while offset < len(data):
            light = {}
            light['type'], offset = decode_uint8(data, offset)
            light['unknown'], offset = decode_uint8(data, offset)
            light['att_start'], offset = decode_float(data, offset)
            light['att_end'], offset = decode_float(data, offset)
            light['color'], offset = decode_RGBA(data, offset)
            lights.append(light)
        decoded = {'lights': lights}
        logging.debug(f"MOLT Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MOLT chunk: {e}")
        return None, offset

def decode_MODS(data, offset=0):
    try:
        doodad_sets = []
        while offset < len(data):
            doodad_set = {}
            doodad_set['name'], offset = decode_cstring(data, offset, 20)
            doodad_set['start_doodad'], offset = decode_uint32(data, offset)
            doodad_set['n_doodads'], offset = decode_uint32(data, offset)
            doodad_set['padding'], offset = decode_uint32(data, offset)
            doodad_sets.append(doodad_set)
        decoded = {'doodad_sets': doodad_sets}
        logging.debug(f"MODS Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MODS chunk: {e}")
        return None, offset

def decode_MODN(data, offset=0):
    try:
        doodad_names = []
        while offset < len(data):
            name, offset = decode_cstring(data, offset, len(data) - offset)
            doodad_names.append(name)
        decoded = {'doodad_names': doodad_names}
        logging.debug(f"MODN Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MODN chunk: {e}")
        return None, offset

def decode_MODD(data, offset=0):
    try:
        doodads = []
        while offset < len(data):
            doodad = {}
            doodad['name_id'], offset = decode_uint32(data, offset)
            doodad['unique_id'], offset = decode_uint32(data, offset)
            doodad['position'], offset = decode_C3Vector(data, offset)
            doodad['rotation'], offset = decode_C3Vector(data, offset)
            doodad['scale'], offset = decode_float(data, offset)
            doodad['color'], offset = decode_RGBA(data, offset)
            doodads.append(doodad)
        decoded = {'doodads': doodads}
        logging.debug(f"MODD Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MODD chunk: {e}")
        return None, offset

def decode_MFOG(data, offset=0):
    try:
        fogs = []
        while offset < len(data):
            fog = {}
            fog['flags'], offset = decode_uint32(data, offset)
            fog['position'], offset = decode_C3Vector(data, offset)
            fog['small_radius'], offset = decode_float(data, offset)
            fog['big_radius'], offset = decode_float(data, offset)
            fog['end_dist'], offset = decode_float(data, offset)
            fog['start_factor'], offset = decode_float(data, offset)
            fog['color1'], offset = decode_RGBA(data, offset)
            fog['end_dist2'], offset = decode_float(data, offset)
            fog['start_factor2'], offset = decode_float(data, offset)
            fog['color2'], offset = decode_RGBA(data, offset)
            fogs.append(fog)
        decoded = {'fogs': fogs}
        logging.debug(f"MFOG Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MFOG chunk: {e}")
        return None, offset

wmo_root_chunk_decoders = {
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
}

def decode_chunk(data, offset=0):
    chunk_id = data[offset:offset + 4].decode('utf-8')
    chunk_size = int.from_bytes(data[offset + 4:offset + 8], byteorder='little')
    chunk_data = data[offset + 8:offset + 8 + chunk_size]
    offset += 8 + chunk_size

    decoder = wmo_root_chunk_decoders.get(chunk_id) or wmo_root_chunk_decoders.get(reverse_chunk_id(chunk_id))
    if decoder:
        decoded_data, _ = decoder(chunk_data, 0)
        return decoded_data, offset
    else:
        logging.warning(f"No decoder for chunk: {chunk_id}")
        return {'raw_data': chunk_data.hex()}, offset

def parse_wmo_root(file_path):
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
