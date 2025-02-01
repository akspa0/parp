import struct
import logging

# Decoders for ADT sub-chunks
def decode_MCVT(data):
    """Decode the MCVT (vertex height map) sub-chunk."""
    heights = struct.unpack(f'<{len(data)//4}f', data)
    return {'heights': heights}, len(data)

def decode_MCLY(data):
    """Decode the MCLY (layer definitions) sub-chunk."""
    layers = []
    layer_format = '<IB3xI'
    layer_size = struct.calcsize(layer_format)

    for i in range(0, len(data), layer_size):
        texture_id, flags, offset_in_mcal = struct.unpack_from(layer_format, data, i)
        layers.append({'texture_id': texture_id, 'flags': flags, 'offset_in_mcal': offset_in_mcal})

    return {'layers': layers}, len(data)

def decode_MCAL(data):
    """Decode the MCAL (alpha map) sub-chunk."""
    # Parsing depends on flags in MCLY, assuming raw data for now
    return {'alpha_data': data.hex()}, len(data)

def decode_MCRF(data):
    """Decode the MCRF (doodad references) sub-chunk."""
    references = struct.unpack(f'<{len(data)//4}I', data)
    return {'references': references}, len(data)

def decode_MCSH(data):
    """Decode the MCSH (shadow map) sub-chunk."""
    return {'shadow_map': list(data)}, len(data)

def decode_MCCV(data):
    """Decode the MCCV (vertex colors) sub-chunk."""
    colors = []
    color_format = '<4B'
    color_size = struct.calcsize(color_format)

    for i in range(0, len(data), color_size):
        r, g, b, a = struct.unpack_from(color_format, data, i)
        colors.append({'r': r, 'g': g, 'b': b, 'a': a})

    return {'vertex_colors': colors}, len(data)

def decode_MCLQ(data):
    """Decode the MCLQ (liquid data) sub-chunk."""
    # Placeholder for liquid data decoding
    return {'liquid_data': data.hex()}, len(data)

def decode_MCSE(data):
    """Decode the MCSE (sound emitters) sub-chunk."""
    emitters = []
    emitter_format = '<3f2I'
    emitter_size = struct.calcsize(emitter_format)

    for i in range(0, len(data), emitter_size):
        position = struct.unpack_from('<3f', data, i)
        sound_id, unknown = struct.unpack_from('<2I', data, i + 12)
        emitters.append({'position': position, 'sound_id': sound_id, 'unknown': unknown})

    return {'sound_emitters': emitters}, len(data)

# Dictionary mapping sub-chunk IDs to decoder functions
sub_chunk_decoders = {
    'MCVT': decode_MCVT,
    'MCLY': decode_MCLY,
    'MCAL': decode_MCAL,
    'MCRF': decode_MCRF,
    'MCSH': decode_MCSH,
    'MCCV': decode_MCCV,
    'MCLQ': decode_MCLQ,
    'MCSE': decode_MCSE,
}

logging.info("Sub-chunk decoders initialized.")
