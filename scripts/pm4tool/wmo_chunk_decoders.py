import struct
import logging
from common_helpers import decode_uint32, decode_float, decode_cstring, decode_C3Vector, decode_C3Vector_i, decode_RGBA, read_chunks_from_data

# Decoding functions for each chunk type

def decode_chunk_REVM(data, offset):
    return decode_chunk_MVER(data, offset)

def decode_chunk_MVER(data, offset):
    version, offset = decode_uint32(data, offset)
    return {'version': version}, offset

def decode_chunk_MOGP(data, offset):
    parsed_sub_chunks = {}
    sub_chunks, _ = read_chunks_from_data(data[offset:])
    
    for sub_chunk_id, sub_chunk_data in sub_chunks.items():
        try:
            sub_chunk_id_str = sub_chunk_id.decode('utf-8', errors='ignore')
            logging.info(f"Decoding sub-chunk: {sub_chunk_id_str} (or {sub_chunk_id.hex()})")
            parsed_sub_chunk, _ = decode_chunk(sub_chunk_id_str, sub_chunk_data)
            parsed_sub_chunks[sub_chunk_id_str] = parsed_sub_chunk
        except UnicodeDecodeError:
            logging.error(f"Error decoding sub-chunk ID: {sub_chunk_id}")
            continue
        except Exception as e:
            logging.error(f"Error decoding sub-chunk {sub_chunk_id}: {e}")
            continue

    return parsed_sub_chunks, offset

def decode_chunk_MOPY(data, offset):
    flags, offset = decode_uint32(data, offset)
    material_id, offset = decode_uint32(data, offset)
    return {'flags': flags, 'material_id': material_id}, offset

def decode_chunk_MOVI(data, offset):
    indices = []
    while offset < len(data):
        index, offset = decode_uint32(data, offset)
        indices.append(index)
    return {'indices': indices}, offset

def decode_chunk_MOLT(data, offset):
    lights = []
    while offset < len(data):
        light = {}
        light['type'], offset = decode_uint32(data, offset)
        light['diffuse_color'], offset = decode_RGBA(data, offset)
        light['intensity'], offset = decode_float(data, offset)
        light['position'], offset = decode_C3Vector(data, offset)
        lights.append(light)
    return {'lights': lights}, offset

def decode_chunk_MOSB(data, offset):
    sound_data = []
    while offset < len(data):
        sound = {}
        sound['sound_id'], offset = decode_uint32(data, offset)
        sound_data.append(sound)
    return {'sounds': sound_data}, offset

def decode_chunk_MOCV(data, offset):
    colors = []
    while offset < len(data):
        color = {}
        color['color'], offset = decode_RGBA(data, offset)
        colors.append(color)
    return {'colors': colors}, offset

def decode_chunk_MODD(data, offset):
    doodads = []
    while offset < len(data):
        doodad = {}
        doodad['name_offset'], offset = decode_uint32(data, offset)
        doodad['position'], offset = decode_C3Vector(data, offset)
        doodad['rotation'], offset = decode_C3Vector(data, offset)
        doodad['scale'], offset = decode_float(data, offset)
        doodad['color'], offset = decode_RGBA(data, offset)
        doodads.append(doodad)
    return {'doodads': doodads}, offset

def decode_chunk_MODR(data, offset):
    references = []
    while offset < len(data):
        reference = {}
        reference['doodad_id'], offset = decode_uint32(data, offset)
        references.append(reference)
    return {'references': references}, offset

def decode_chunk_MOTV(data, offset):
    textures = []
    while offset < len(data):
        texture = {}
        texture['u'], offset = decode_float(data, offset)
        texture['v'], offset = decode_float(data, offset)
        textures.append(texture)
    return {'textures': textures}, offset

def decode_chunk_MOVT(data, offset):
    vertices = []
    while offset < len(data):
        vertex, offset = decode_C3Vector(data, offset)
        vertices.append(vertex)
    return {'vertices': vertices}, offset

def decode_chunk_MOIN(data, offset):
    indices = []
    while offset < len(data):
        index, offset = decode_uint32(data, offset)
        indices.append(index)
    return {'indices': indices}, offset

def decode_unknown(data, offset):
    return {"data": data[offset:].hex()}, len(data)

chunk_decoders = {
    'REVM': decode_chunk_REVM,
    'MVER': decode_chunk_MVER,
    'MOGP': decode_chunk_MOGP,
    'MOPY': decode_chunk_MOPY,
    'MOVI': decode_chunk_MOVI,
    'MOLT': decode_chunk_MOLT,
    'MOSB': decode_chunk_MOSB,
    'MOCV': decode_chunk_MOCV,
    'MODD': decode_chunk_MODD,
    'MODR': decode_chunk_MODR,
    'MOTV': decode_chunk_MOTV,
    'MOVT': decode_chunk_MOVT,
    'MOIN': decode_chunk_MOIN,
    'default': decode_unknown
}

def decode_chunk(chunk_id, data, offset=0):
    chunk_id_str = chunk_id.decode('utf-8', errors='ignore') if isinstance(chunk_id, bytes) else chunk_id
    chunk_id_str = chunk_id_str if chunk_id_str in chunk_decoders else reverse_chunk_id(chunk_id).hex()
    return chunk_decoders.get(chunk_id_str, chunk_decoders['default'])(data, offset)

def reverse_chunk_id(chunk_id):
    return chunk_id[::-1]
