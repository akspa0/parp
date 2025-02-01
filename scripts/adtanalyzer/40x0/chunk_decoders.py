import struct
import logging
from decoding_logic import decode_flags, parse_offsets

# Decoders for Terrain-related chunks
def decode_MCNK(data):
    """Decode the MCNK (map chunk) and its sub-chunks."""
    header_format = '<I2H10I3f2I'
    header_size = struct.calcsize(header_format)
    header = struct.unpack(header_format, data[:header_size])

    subchunks = {}
    offsets = {
        'MCVT': header[5],
        'MCLY': header[6],
        'MCAL': header[8],
        'MCSH': header[10],
        'MCLQ': header[14],
    }
    sizes = {
        'MCAL': header[9],
        'MCSH': header[11],
        'MCLQ': header[15],
    }

    for subchunk_id, offset in offsets.items():
        if offset == 0:
            continue

        subchunk_size = sizes.get(subchunk_id, None)
        subchunk_data = data[offset:offset + subchunk_size] if subchunk_size else data[offset:]

        try:
            subchunk_decoder = globals().get(f'decode_{subchunk_id}')
            if subchunk_decoder:
                subchunks[subchunk_id] = subchunk_decoder(subchunk_data)
            else:
                logging.warning(f"No decoder found for subchunk {subchunk_id}. Skipping.")
        except Exception as e:
            logging.error(f"Error decoding subchunk {subchunk_id}: {e}")

    return {
        'header': header,
        'subchunks': subchunks
    }, len(data)

def decode_MCVT(data):
    """Decode the MCVT (vertex height map) subchunk."""
    heights = struct.unpack(f'<{len(data)//4}f', data)
    return {'heights': heights}, len(data)

def decode_MCLY(data):
    """Decode the MCLY (layer definitions) subchunk."""
    layer_format = '<IB3xI'
    layer_size = struct.calcsize(layer_format)
    layers = []

    for i in range(0, len(data), layer_size):
        if i + layer_size > len(data):
            logging.warning(f"Skipping incomplete MCLY entry at offset {i}.")
            break

        try:
            texture_id, flags, offset_in_mcal = struct.unpack_from(layer_format, data, i)
            layers.append({
                'texture_id': texture_id,
                'flags': decode_flags(flags),
                'offset_in_mcal': offset_in_mcal
            })
        except Exception as e:
            logging.error(f"Error decoding MCLY entry at offset {i}: {e}")
            continue

    return {'layers': layers}, len(data)

def decode_MH2O(data):
    """Decode the MH2O (water data) chunk."""
    return parse_offsets(data, '<I2H', '<4I')

# Decoders for Texture-related chunks
def decode_MTEX(data):
    """Decode the MTEX (texture paths) chunk."""
    textures = data.decode('utf-8').split('\x00')[:-1]
    return {'textures': textures}, len(data)

# Decoders for Object-related chunks
def decode_MDDF(data):
    """Decode the MDDF (doodad placement definitions) chunk."""
    entries = []
    entry_format = '<3I3f2H'
    entry_size = struct.calcsize(entry_format)
    for i in range(0, len(data), entry_size):
        entry = struct.unpack_from(entry_format, data, i)
        entries.append({
            'nameId': entry[0],
            'uniqueId': entry[1],
            'position': {'x': entry[2], 'y': entry[3], 'z': entry[4]},
            'rotation': {'x': entry[5], 'y': entry[6], 'z': entry[7]},
            'scale': entry[8],
            'flags': entry[9]
        })
    return {'entries': entries}, len(data)

# Decoders for General ADT chunks
def decode_MVER(data):
    """Decode the MVER (version) chunk."""
    version = struct.unpack('<I', data[:4])[0]
    return {'version': version}, len(data)

def decode_MHDR(data):
    """Decode the MHDR (header) chunk."""
    header_format = '<8I'
    header_size = struct.calcsize(header_format)
    if len(data) < header_size:
        raise ValueError("MHDR chunk is too small to decode.")
    offsets = struct.unpack(header_format, data[:header_size])
    return {
        'flags': offsets[0],
        'ofsMCIN': offsets[1],
        'ofsMTEX': offsets[2],
        'ofsMMDX': offsets[3],
        'ofsMMID': offsets[4],
        'ofsMWMO': offsets[5],
        'ofsMWID': offsets[6],
        'ofsMDDF': offsets[7]
    }, len(data)

# Combine all decoders into a dictionary
decoders = {
    'MCNK': decode_MCNK,
    'MCVT': decode_MCVT,
    'MCLY': decode_MCLY,
    'MH2O': decode_MH2O,
    'MTEX': decode_MTEX,
    'MDDF': decode_MDDF,
    'MVER': decode_MVER,
    'MHDR': decode_MHDR,
}
