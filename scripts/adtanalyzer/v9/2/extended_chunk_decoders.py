import struct

# Additional decoders for ADT chunks
def decode_MCNR(data):
    """Decode the MCNR (normal vector data) chunk."""
    normals = []
    vector_format = '<fff'
    vector_size = struct.calcsize(vector_format)
    for i in range(0, len(data), vector_size):
        normal = struct.unpack_from(vector_format, data, i)
        normals.append({'x': normal[0], 'y': normal[1], 'z': normal[2]})
    return {'normals': normals}, len(data)

def decode_MCVT(data):
    """Decode the MCVT (vertex height map) chunk."""
    heights = struct.unpack(f'<{len(data)//4}f', data)
    return {'heights': list(heights)}, len(data)

def decode_MCLY(data):
    """Decode the MCLY (layer definitions) chunk."""
    layers = []
    layer_format = '<IB3xI'
    layer_size = struct.calcsize(layer_format)
    for i in range(0, len(data), layer_size):
        texture_id, flags, offset_in_mcal = struct.unpack_from(layer_format, data, i)
        layers.append({'texture_id': texture_id, 'flags': flags, 'offset_in_mcal': offset_in_mcal})
    return {'layers': layers}, len(data)

def decode_MCAL(data):
    """Decode the MCAL (alpha map) chunk."""
    # Parsing depends on flags in MCLY; returning raw data for now
    return {'alpha_data': data.hex()}, len(data)

def decode_MCRF(data):
    """Decode the MCRF (doodad references) chunk."""
    references = struct.unpack(f'<{len(data)//4}I', data)
    return {'references': list(references)}, len(data)

def decode_MCSE(data):
    """Decode the MCSE (sound emitters) chunk."""
    emitters = []
    emitter_format = '<3f2I'
    emitter_size = struct.calcsize(emitter_format)
    for i in range(0, len(data), emitter_size):
        position = struct.unpack_from('<3f', data, i)
        sound_id, unknown = struct.unpack_from('<2I', data, i + 12)
        emitters.append({'position': {'x': position[0], 'y': position[1], 'z': position[2]}, 'sound_id': sound_id, 'unknown': unknown})
    return {'sound_emitters': emitters}, len(data)

def decode_MTEX(data):
    """Decode the MTEX (texture file paths) chunk."""
    texture_names = data.decode('utf-8').split('\x00')[:-1]
    return {'textures': texture_names}, len(data)

# Map of additional decoders
extended_chunk_decoders = {
    'MCNR': decode_MCNR,
    'MCVT': decode_MCVT,
    'MCLY': decode_MCLY,
    'MCAL': decode_MCAL,
    'MCRF': decode_MCRF,
    'MCSE': decode_MCSE,
    'MTEX': decode_MTEX,
}
