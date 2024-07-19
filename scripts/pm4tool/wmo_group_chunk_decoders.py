import logging
from common_helpers import decode_uint8, decode_uint16, decode_uint32, decode_float, decode_cstring, decode_C3Vector, decode_RGBA

def reverse_chunk_id(chunk_id):
    return chunk_id[::-1]

def decode_MOGP(data, offset=0):
    try:
        group = {}
        group['name_ofs'], offset = decode_uint32(data, offset)
        group['desc_group_name'], offset = decode_uint32(data, offset)
        group['flags'], offset = decode_uint32(data, offset)
        group['bounding_box_corner1'], offset = decode_C3Vector(data, offset)
        group['bounding_box_corner2'], offset = decode_C3Vector(data, offset)
        group['portal_start'], offset = decode_uint16(data, offset)
        group['portal_count'], offset = decode_uint16(data, offset)
        group['batch_a'], offset = decode_uint16(data, offset)
        group['batch_b'], offset = decode_uint16(data, offset)
        group['batch_c'], offset = decode_uint16(data, offset)
        group['batch_d'], offset = decode_uint16(data, offset)
        group['n_batches'], offset = decode_uint16(data, offset)
        group['fog_indices'], offset = decode_uint16(data, offset)
        group['liquid_type'], offset = decode_uint32(data, offset)
        group['group_id'], offset = decode_uint32(data, offset)
        logging.debug(f"MOGP Chunk: {group}")
        return group, offset
    except Exception as e:
        logging.error(f"Error decoding MOGP chunk: {e}")
        return None, offset

def decode_MOPY(data, offset=0):
    try:
        materials = []
        while offset < len(data):
            material = {}
            material['flags'], offset = decode_uint8(data, offset)
            material['material_id'], offset = decode_uint8(data, offset)
            materials.append(material)
        decoded = {'materials': materials}
        logging.debug(f"MOPY Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MOPY chunk: {e}")
        return None, offset

def decode_MOVI(data, offset=0):
    try:
        indices = []
        while offset < len(data):
            index, offset = decode_uint16(data, offset)
            indices.append(index)
        decoded = {'triangle_indices': indices}
        logging.debug(f"MOVI Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MOVI chunk: {e}")
        return None, offset

def decode_MOVT(data, offset=0):
    try:
        vertices = []
        while offset < len(data):
            vertex, offset = decode_C3Vector(data, offset)
            vertices.append(vertex)
        decoded = {'vertices': vertices}
        logging.debug(f"MOVT Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MOVT chunk: {e}")
        return None, offset

def decode_MONR(data, offset=0):
    try:
        normals = []
        while offset < len(data):
            normal, offset = decode_C3Vector(data, offset)
            normals.append(normal)
        decoded = {'normals': normals}
        logging.debug(f"MONR Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MONR chunk: {e}")
        return None, offset

def decode_MOTV(data, offset=0):
    try:
        tex_coords = []
        while offset < len(data):
            tex_coord, offset = decode_C3Vector(data, offset)
            tex_coords.append(tex_coord)
        decoded = {'tex_coords': tex_coords}
        logging.debug(f"MOTV Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MOTV chunk: {e}")
        return None, offset

def decode_MOBA(data, offset=0):
    try:
        batches = []
        while offset < len(data):
            batch = {}
            batch['start_index'], offset = decode_uint16(data, offset)
            batch['count'], offset = decode_uint16(data, offset)
            batch['portal_index'], offset = decode_uint16(data, offset)
            batch['t_type'], offset = decode_uint16(data, offset)
            batch['type2'], offset = decode_uint16(data, offset)
            batch['flags'], offset = decode_uint16(data, offset)
            batches.append(batch)
        decoded = {'batches': batches}
        logging.debug(f"MOBA Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MOBA chunk: {e}")
        return None, offset

def decode_MOLR(data, offset=0):
    try:
        lights = []
        while offset < len(data):
            light, offset = decode_uint16(data, offset)
            lights.append(light)
        decoded = {'lights': lights}
        logging.debug(f"MOLR Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MOLR chunk: {e}")
        return None, offset

def decode_MODR(data, offset=0):
    try:
        doodads = []
        while offset < len(data):
            doodad, offset = decode_uint16(data, offset)
            doodads.append(doodad)
        decoded = {'doodads': doodads}
        logging.debug(f"MODR Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MODR chunk: {e}")
        return None, offset

def decode_MOBN(data, offset=0):
    try:
        nodes = []
        while offset < len(data):
            node = {}
            node['flags'], offset = decode_uint32(data, offset)
            node['neg_child'], offset = decode_uint32(data, offset)
            node['pos_child'], offset = decode_uint32(data, offset)
            node['n_faces'], offset = decode_uint32(data, offset)
            node['faces_start'], offset = decode_uint32(data, offset)
            node['plane_distance'], offset = decode_float(data, offset)
            node['plane_normal'], offset = decode_C3Vector(data, offset)
            nodes.append(node)
        decoded = {'nodes': nodes}
        logging.debug(f"MOBN Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MOBN chunk: {e}")
        return None, offset

def decode_MOBR(data, offset=0):
    try:
        render_batches = []
        while offset < len(data):
            batch = {}
            batch['face_start'], offset = decode_uint16(data, offset)
            batch['n_faces'], offset = decode_uint16(data, offset)
            batch['group'], offset = decode_uint16(data, offset)
            render_batches.append(batch)
        decoded = {'render_batches': render_batches}
        logging.debug(f"MOBR Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MOBR chunk: {e}")
        return None, offset

def decode_MOCV(data, offset=0):
    try:
        colors = []
        while offset < len(data):
            color = {}
            color['r'], offset = decode_uint8(data, offset)
            color['g'], offset = decode_uint8(data, offset)
            color['b'], offset = decode_uint8(data, offset)
            color['a'], offset = decode_uint8(data, offset)
            colors.append(color)
        decoded = {'colors': colors}
        logging.debug(f"MOCV Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MOCV chunk: {e}")
        return None, offset

def decode_MLIQ(data, offset=0):
    try:
        liquids = []
        while offset < len(data):
            liquid = {}
            liquid['xverts'], offset = decode_uint32(data, offset)
            liquid['yverts'], offset = decode_uint32(data, offset)
            liquid['xfmverts'], offset = decode_uint32(data, offset)
            liquid['yfmverts'], offset = decode_uint32(data, offset)
            liquid['layer_count'], offset = decode_uint32(data, offset)
            liquid['material_id'], offset = decode_uint32(data, offset)
            liquids.append(liquid)
        decoded = {'liquids': liquids}
        logging.debug(f"MLIQ Chunk: {decoded}")
        return decoded, offset
    except Exception as e:
        logging.error(f"Error decoding MLIQ chunk: {e}")
        return None, offset

wmo_group_chunk_decoders = {
    'MOGP': decode_MOGP,
    'MOPY': decode_MOPY,
    'MOVI': decode_MOVI,
    'MOVT': decode_MOVT,
    'MONR': decode_MONR,
    'MOTV': decode_MOTV,
    'MOBA': decode_MOBA,
    'MOLR': decode_MOLR,
    'MODR': decode_MODR,
    'MOBN': decode_MOBN,
    'MOBR': decode_MOBR,
    'MOCV': decode_MOCV,
    'MLIQ': decode_MLIQ,
}

def decode_chunk(data, offset=0):
    chunk_id = data[offset:offset + 4].decode('utf-8')
    chunk_size = int.from_bytes(data[offset + 4:offset + 8], byteorder='little')
    chunk_data = data[offset + 8:offset + 8 + chunk_size]
    offset += 8 + chunk_size

    decoder = wmo_group_chunk_decoders.get(chunk_id) or wmo_group_chunk_decoders.get(reverse_chunk_id(chunk_id))
    if decoder:
        decoded_data, _ = decoder(chunk_data, 0)
        return decoded_data, offset
    else:
        logging.warning(f"No decoder for chunk: {chunk_id}")
        return {'raw_data': chunk_data.hex()}, offset

def parse_wmo_group(file_path):
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
