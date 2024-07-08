# chunk_decoders.py
import struct
import logging

# Common type decoders
def decode_uint8(data, offset):
    return struct.unpack_from('B', data, offset)[0], offset + 1

def decode_uint16(data, offset):
    return struct.unpack_from('H', data, offset)[0], offset + 2

def decode_uint32(data, offset):
    return struct.unpack_from('I', data, offset)[0], offset + 4

def decode_float(data, offset):
    return struct.unpack_from('f', data, offset)[0], offset + 4

def decode_cstring(data, offset):
    end = data.find(b'\x00', offset)
    return data[offset:end].decode('ascii'), end + 1

def decode_C3Vector(data, offset):
    x, offset = decode_float(data, offset)
    y, offset = decode_float(data, offset)
    z, offset = decode_float(data, offset)
    return {'x': x, 'y': y, 'z': z}, offset

def decode_C3Vector_i(data, offset):
    x, offset = decode_uint32(data, offset)
    y, offset = decode_uint32(data, offset)
    z, offset = decode_uint32(data, offset)
    return {'x': x, 'y': y, 'z': z}, offset

def decode_RGBA(data, offset):
    r, offset = decode_uint8(data, offset)
    g, offset = decode_uint8(data, offset)
    b, offset = decode_uint8(data, offset)
    a, offset = decode_uint8(data, offset)
    return {'r': r, 'g': g, 'b': b, 'a': a}, offset

# Specific chunk decoders using common types
def decode_REVM_chunk(data):
    offset = 0
    decoded = {}
    decoded['version'], offset = decode_uint32(data, offset)
    logging.debug(f"REVM Chunk: {decoded}")
    return decoded

def decode_CRCM_chunk(data):
    offset = 0
    decoded = {}
    decoded['_0x00'], offset = decode_uint32(data, offset)
    logging.debug(f"CRCM Chunk: {decoded}")
    return decoded

def decode_DHSM_chunk(data):
    offset = 0
    decoded = {}
    decoded['_0x00'], offset = decode_uint32(data, offset)
    decoded['_0x04'], offset = decode_uint32(data, offset)
    decoded['_0x08'], offset = decode_uint32(data, offset)
    decoded['_0x0c'] = [decode_uint32(data, offset + i*4)[0] for i in range(5)]
    logging.debug(f"DHSM Chunk: {decoded}")
    return decoded

def decode_VPSM_chunk(data):
    offset = 0
    decoded = []
    while offset < len(data):
        vertex, offset = decode_C3Vector(data, offset)
        decoded.append(vertex)
    logging.debug(f"VPSM Chunk: {decoded}")
    return decoded

def decode_IPSM_chunk(data):
    offset = 0
    decoded = []
    while offset < len(data):
        index, offset = decode_uint32(data, offset)
        decoded.append(index)
    logging.debug(f"IPSM Chunk: {decoded}")
    return decoded

def decode_NCMS_chunk(data):
    offset = 0
    decoded = []
    while offset < len(data):
        vector, offset = decode_C3Vector(data, offset)
        decoded.append(vector)
    logging.debug(f"NCMS Chunk: {decoded}")
    return decoded

def decode_KLMS_chunk(data):
    offset = 0
    decoded = []
    while offset < len(data):
        entry = {}
        entry['_0x00'], offset = decode_uint8(data, offset)
        entry['_0x01'], offset = decode_uint8(data, offset)
        entry['_0x02'], offset = decode_uint16(data, offset)
        entry['_0x04'], offset = decode_uint32(data, offset)
        entry['MSPI_first_index'], offset = decode_uint32(data, offset)
        entry['MSPI_index_count'], offset = decode_uint8(data, offset)
        entry['_0x0c'], offset = decode_uint32(data, offset)
        entry['_0x10'], offset = decode_uint16(data, offset)
        entry['_0x12'], offset = decode_uint16(data, offset)
        decoded.append(entry)
    logging.debug(f"KLMS Chunk: {decoded}")
    return decoded

def decode_TVSM_chunk(data):
    offset = 0
    decoded = []
    while offset < len(data):
        vertex, offset = decode_C3Vector(data, offset)
        decoded.append(vertex)
    logging.debug(f"TVSM Chunk: {decoded}")
    return decoded

def decode_IVSM_chunk(data):
    offset = 0
    decoded = []
    while offset < len(data):
        index, offset = decode_uint32(data, offset)
        decoded.append(index)
    logging.debug(f"IVSM Chunk: {decoded}")
    return decoded

def decode_RUSM_chunk(data):
    offset = 0
    decoded = []
    while offset < len(data):
        entry = {}
        entry['_0x00'], offset = decode_uint8(data, offset)
        entry['_0x01'], offset = decode_uint8(data, offset)
        entry['_0x02'], offset = decode_uint8(data, offset)
        entry['_0x03'], offset = decode_uint8(data, offset)
        entry['_0x04'], offset = decode_float(data, offset)
        entry['_0x08'], offset = decode_float(data, offset)
        entry['_0x0c'], offset = decode_float(data, offset)
        entry['_0x10'], offset = decode_float(data, offset)
        entry['MSVI_first_index'], offset = decode_uint32(data, offset)
        entry['_0x18'], offset = decode_uint32(data, offset)
        entry['_0x1c'], offset = decode_uint32(data, offset)
        decoded.append(entry)
    logging.debug(f"RUSM Chunk: {decoded}")
    return decoded

def decode_LRPM_chunk(data):
    offset = 0
    decoded = []
    entry_size = 24
    num_entries = len(data) // entry_size

    for i in range(num_entries):
        entry_data = struct.unpack_from('6f', data, offset)
        offset += entry_size
        tilt_x_value = entry_data[1]
        tilt_y_value = entry_data[5]
        position_data = [coord / 36 for coord in entry_data[2:5]]
        decoded.append({
            'tilt_x': tilt_x_value,
            'tilt_y': tilt_y_value,
            'position_data': position_data
        })
    logging.debug(f"LRPM Chunk: {decoded}")
    return decoded

def decode_RRPM_chunk(data):
    offset = 0
    decoded = []
    entry_size = 24
    num_entries = len(data) // entry_size

    for i in range(num_entries):
        entry_data = struct.unpack_from('6f', data, offset)
        offset += entry_size
        position_data = [coord * 36 for coord in entry_data]
        decoded.append(position_data)
    logging.debug(f"RRPM Chunk: {decoded}")
    return decoded

def decode_HBDM_chunk(data):
    offset = 0
    decoded = {}
    decoded['count'], offset = decode_uint32(data, offset)
    decoded['entries'] = []

    entry = {'index': None, 'filenames': []}
    while offset < len(data):
        sub_chunk_id = data[offset:offset+4].decode('utf-8')
        sub_chunk_size, sub_offset = decode_uint32(data, offset + 4)
        sub_chunk_data = data[sub_offset:sub_offset + sub_chunk_size]
        offset = sub_offset + sub_chunk_size

        if sub_chunk_id == 'IBDM':
            if entry['index'] is not None or entry['filenames']:  # Save the previous entry if not empty
                decoded['entries'].append(entry)
            entry = {'index': None, 'filenames': []}
            entry['index'], _ = decode_uint32(sub_chunk_data, 0)
        elif sub_chunk_id == 'FBDM':
            sub_sub_offset = 0
            while sub_sub_offset < len(sub_chunk_data):
                filename, sub_sub_offset = decode_cstring(sub_chunk_data, sub_sub_offset)
                entry['filenames'].append(filename)

    if entry['index'] is not None or entry['filenames']:  # Save the last entry if not empty
        decoded['entries'].append(entry)

    logging.debug(f"HBDM Chunk: {decoded}")
    return decoded

def decode_IBDM_chunk(data):
    offset = 0
    decoded = {}
    decoded['m_destructible_building_index'], offset = decode_uint32(data, offset)
    logging.debug(f"IBDM Chunk: {decoded}")
    return decoded

def decode_FBDM_chunk(data):
    decoded = []
    offset = 0
    while offset < len(data):
        filename, offset = decode_cstring(data, offset)
        decoded.append(filename)
    logging.debug(f"FBDM Chunk: {decoded}")
    return decoded

def decode_SODM_chunk(data):
    offset = 0
    decoded = {}
    decoded['value'], offset = decode_uint32(data, offset)
    logging.debug(f"SODM Chunk: {decoded}")
    return decoded

def decode_FSDM_chunk(data):
    offset = 0
    decoded = []
    while offset < len(data):
        value, offset = decode_uint32(data, offset)
        decoded.append(value)
    logging.debug(f"FSDM Chunk: {decoded}")
    return decoded

# Mapping chunk IDs to their decoders
chunk_decoders = {
    'MVER': decode_REVM_chunk,
    'MCRC': decode_CRCM_chunk,
    'MSHD': decode_DHSM_chunk,
    'MSPV': decode_VPSM_chunk,
    'MSPI': decode_IPSM_chunk,
    'MSCN': decode_NCMS_chunk,
    'MSLK': decode_KLMS_chunk,
    'MSVT': decode_TVSM_chunk,
    'MSVI': decode_IVSM_chunk,
    'MSUR': decode_RUSM_chunk,
    'LRPM': decode_LRPM_chunk,
    'RRPM': decode_RRPM_chunk,
    'HBDM': decode_HBDM_chunk,
    'IBDM': decode_IBDM_chunk,
    'FBDM': decode_FBDM_chunk,
    'SODM': decode_SODM_chunk,
    'FSDM': decode_FSDM_chunk,
    # Add more mappings for other chunk types as we define them...
}
