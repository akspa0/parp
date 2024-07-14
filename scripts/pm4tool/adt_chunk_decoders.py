import logging
import struct
from common_helpers import (
    decode_uint8,
    decode_uint16,
    decode_int16,
    decode_uint32,
    decode_float,
    decode_cstring,
    decode_C3Vector,
    decode_C3Vector_i,
    decode_RGBA
)

# Function to reverse chunk IDs
def reverse_chunk_id(chunk_id):
    return chunk_id[::-1]

# Decoders for ADT chunks
def decode_MVER(data, offset=0):
    version, offset = decode_uint32(data, offset)
    return {'version': version}

def decode_MHDR(data, offset=0):
    header = {}
    header['flags'], offset = decode_uint32(data, offset)
    header['offsMCIN'], offset = decode_uint32(data, offset)
    header['offsMTEX'], offset = decode_uint32(data, offset)
    header['offsMMDX'], offset = decode_uint32(data, offset)
    header['offsMMID'], offset = decode_uint32(data, offset)
    header['offsMWMO'], offset = decode_uint32(data, offset)
    header['offsMWID'], offset = decode_uint32(data, offset)
    header['offsMDDF'], offset = decode_uint32(data, offset)
    header['offsMODF'], offset = decode_uint32(data, offset)
    header['offsMFBO'], offset = decode_uint32(data, offset)
    header['offsMH2O'], offset = decode_uint32(data, offset)
    header['offsMTXF'], offset = decode_uint32(data, offset)
    return header

def decode_MCIN(data, offset=0):
    entries = []
    for _ in range(256):
        entry = {}
        entry['offset'], offset = decode_uint32(data, offset)
        entry['size'], offset = decode_uint32(data, offset)
        entry['flags'], offset = decode_uint32(data, offset)
        entry['asyncId'], offset = decode_uint32(data, offset)
        entries.append(entry)
    return {'entries': entries}

def decode_MTXF(data, offset=0):
    return {'MTXF_data': data[offset:].hex()}

def decode_MMDX(data, offset=0):
    strings = []
    while offset < len(data):
        string, offset = decode_cstring(data, offset, len(data) - offset)
        strings.append(string)
    return {'strings': strings}

def decode_MMID(data, offset=0):
    offsets = []
    while offset < len(data):
        off, offset = decode_uint32(data, offset)
        offsets.append(off)
    return {'offsets': offsets}

def decode_MWMO(data, offset=0):
    strings = []
    while offset < len(data):
        string, offset = decode_cstring(data, offset, len(data) - offset)
        strings.append(string)
    return {'strings': strings}

def decode_MWID(data, offset=0):
    offsets = []
    while offset < len(data):
        off, offset = decode_uint32(data, offset)
        offsets.append(off)
    return {'offsets': offsets}

def decode_MDDF(data, offset=0):
    entries = []
    entry_size = 36
    for _ in range(len(data) // entry_size):
        entry = {}
        entry['nameId'], offset = decode_uint32(data, offset)
        entry['uniqueId'], offset = decode_uint32(data, offset)
        entry['position'], offset = decode_C3Vector(data, offset)
        entry['rotation'], offset = decode_C3Vector(data, offset)
        entry['scale'], offset = decode_uint16(data, offset)
        entry['flags'], offset = decode_uint16(data, offset)
        entries.append(entry)
    return {'entries': entries}

def decode_MODF(data, offset=0):
    entries = []
    entry_size = 64
    for _ in range(len(data) // entry_size):
        entry = {}
        entry['nameId'], offset = decode_uint32(data, offset)
        entry['uniqueId'], offset = decode_uint32(data, offset)
        entry['position'], offset = decode_C3Vector(data, offset)
        entry['rotation'], offset = decode_C3Vector(data, offset)
        entry['lowerBounds'], offset = decode_C3Vector(data, offset)
        entry['upperBounds'], offset = decode_C3Vector(data, offset)
        entry['flags'], offset = decode_uint16(data, offset)
        entry['doodadSet'], offset = decode_uint16(data, offset)
        entry['nameSet'], offset = decode_uint16(data, offset)
        entry['padding'], offset = decode_uint16(data, offset)
        entries.append(entry)
    return {'entries': entries}

def decode_MFBO(data, offset=0):
    return {'MFBO_data': data[offset:].hex()}

def decode_MH2O(data, offset=0):
    return {'MH2O_data': data[offset:].hex()}

def decode_MCNK(data, offset=0):
    chunk = {}
    chunk['header'] = {}
    chunk['header']['flags'], offset = decode_uint32(data, offset)
    chunk['header']['indexX'], offset = decode_uint32(data, offset)
    chunk['header']['indexY'], offset = decode_uint32(data, offset)
    chunk['header']['nLayers'], offset = decode_uint32(data, offset)
    chunk['header']['nDoodadRefs'], offset = decode_uint32(data, offset)
    chunk['header']['ofsMCVT'], offset = decode_uint32(data, offset)
    chunk['header']['ofsMCLY'], offset = decode_uint32(data, offset)
    chunk['header']['ofsMCRF'], offset = decode_uint32(data, offset)
    chunk['header']['ofsMCAL'], offset = decode_uint32(data, offset)
    chunk['header']['sizeMCAL'], offset = decode_uint32(data, offset)
    chunk['header']['ofsMCSH'], offset = decode_uint32(data, offset)
    chunk['header']['sizeMCSH'], offset = decode_uint32(data, offset)
    chunk['header']['areaId'], offset = decode_uint32(data, offset)
    chunk['header']['nMapObjRefs'], offset = decode_uint32(data, offset)
    chunk['header']['holes'], offset = decode_uint16(data, offset)
    chunk['header']['lowQualityTextureMap'], offset = decode_uint16(data, offset)
    chunk['header']['predTex'], offset = decode_uint32(data, offset)
    chunk['header']['nEffectDoodad'], offset = decode_uint32(data, offset)
    chunk['header']['ofsMCSE'], offset = decode_uint32(data, offset)
    chunk['header']['nSoundEmitters'], offset = decode_uint32(data, offset)
    chunk['header']['ofsMCLQ'], offset = decode_uint32(data, offset)
    chunk['header']['sizeMCLQ'], offset = decode_uint32(data, offset)
    chunk['header']['position'], offset = decode_C3Vector(data, offset)
    chunk['header']['ofsMCCV'], offset = decode_uint32(data, offset)
    chunk['header']['ofsMCLV'], offset = decode_uint32(data, offset)
    chunk['header']['unused'], offset = decode_uint32(data, offset)
    return chunk

def decode_MCVT(data, offset=0):
    heights = []
    while offset < len(data):
        height, offset = decode_float(data, offset)
        heights.append(height)
    return {'heights': heights}

def decode_MCLY(data, offset=0):
    layers = []
    entry_size = 16
    for _ in range(len(data) // entry_size):
        layer = {}
        layer['textureId'], offset = decode_uint32(data, offset)
        layer['flags'], offset = decode_uint32(data, offset)
        layer['offsetInMCAL'], offset = decode_uint32(data, offset)
        layer['effectId'], offset = decode_uint32(data, offset)
        layers.append(layer)
    return {'layers': layers}

def decode_MCRF(data, offset=0):
    doodadRefs = []
    while offset < len(data):
        ref, offset = decode_uint32(data, offset)
        doodadRefs.append(ref)
    return {'doodadRefs': doodadRefs}

def decode_MCAL(data, offset=0):
    return {'MCAL_data': data[offset:].hex()}

def decode_MCSH(data, offset=0):
    shadowMap = []
    while offset < len(data):
        shadow, offset = decode_uint8(data, offset)
        shadowMap.append(shadow)
    return {'shadowMap': shadowMap}

def decode_MCCV(data, offset=0):
    colors = []
    while offset < len(data):
        color, offset = decode_RGBA(data, offset)
        colors.append(color)
    return {'colors': colors}

def decode_MCLQ(data, offset=0):
    return {'MCLQ_data': data[offset:].hex()}

def decode_MCSE(data, offset=0):
    soundEmitters = []
    entry_size = 24
    for _ in range(len(data) // entry_size):
        emitter = {}
        emitter['position'], offset = decode_C3Vector(data, offset)
        emitter['soundId'], offset = decode_uint32(data, offset)
        emitter['unk'], offset = decode_uint32(data, offset)
        soundEmitters.append(emitter)
    return {'soundEmitters': soundEmitters}

def decode_MCLV(data, offset=0):
    lightValues = []
    while offset < len(data):
        light, offset = decode_uint8(data, offset)
        lightValues.append(light)
    return {'lightValues': lightValues}

# Dictionary to map ADT chunk IDs to decoder functions
adt_chunk_decoders = {
    'MVER': decode_MVER,
    'MHDR': decode_MHDR,
    'MCIN': decode_MCIN,
    'MTXF': decode_MTXF,
    'MMDX': decode_MMDX,
    'MMID': decode_MMID,
    'MWMO': decode_MWMO,
    'MWID': decode_MWID,
    'MDDF': decode_MDDF,
    'MODF': decode_MODF,
    'MFBO': decode_MFBO,
    'MH2O': decode_MH2O,
    'MCNK': decode_MCNK,
    'MCVT': decode_MCVT,
    'MCLY': decode_MCLY,
    'MCRF': decode_MCRF,
    'MCAL': decode_MCAL,
    'MCSH': decode_MCSH,
    'MCCV': decode_MCCV,
    'MCLQ': decode_MCLQ,
    'MCSE': decode_MCSE,
    'MCLV': decode_MCLV,
}

# Function to categorize and parse ADT chunks
def parse_adt(file_path):
    with open(file_path, 'rb') as file:
        data = file.read()
    
    offset = 0
    parsed_data = {
        'terrain': {},
        'metadata': {},
        'textures': {},
        'others': {}
    }

    while offset < len(data):
        chunk_id = data[offset:offset + 4].decode('utf-8')
        chunk_size, offset = decode_uint32(data, offset + 4)
        chunk_data = data[offset:offset + chunk_size]
        offset += chunk_size

        decoder = adt_chunk_decoders.get(chunk_id) or adt_chunk_decoders.get(reverse_chunk_id(chunk_id))
        if decoder:
            decoded_data = decoder(chunk_data)
            if chunk_id.startswith('MC'):
                parsed_data['terrain'][chunk_id] = decoded_data
            elif chunk_id.startswith('MT') or chunk_id.startswith('MW'):
                parsed_data['textures'][chunk_id] = decoded_data
            elif chunk_id.startswith('MD') or chunk_id.startswith('MO'):
                parsed_data['metadata'][chunk_id] = decoded_data
            else:
                parsed_data['others'][chunk_id] = decoded_data
        else:
            logging.warning(f"No decoder found for chunk ID {chunk_id}")

    return parsed_data
