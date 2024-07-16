import struct
import logging

def decode_uint8(data, offset):
    return struct.unpack_from('B', data, offset)[0], offset + 1

def decode_uint16(data, offset):
    return struct.unpack_from('H', data, offset)[0], offset + 2

def decode_int16(data, offset):
    return struct.unpack_from('h', data, offset)[0], offset + 2

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

def reverse_chunk_id(chunk_id):
    return chunk_id[::-1]

def decode_MVER_chunk(data):
    offset = 0
    decoded = {}
    decoded['version'], offset = decode_uint32(data, offset)
    logging.debug(f"MVER Chunk: {decoded}")
    return decoded

def decode_MCRC_chunk(data):
    offset = 0
    decoded = {}
    decoded['_0x00'], offset = decode_uint32(data, offset)
    logging.debug(f"MCRC Chunk: {decoded}")
    return decoded

def decode_MSHD_chunk(data):
    offset = 0
    decoded = {}
    decoded['_0x00'], offset = decode_uint32(data, offset)
    decoded['_0x04'], offset = decode_uint32(data, offset)
    decoded['_0x08'], offset = decode_uint32(data, offset)
    decoded['_0x0c'] = [decode_uint32(data, offset + i*4)[0] for i in range(5)]
    logging.debug(f"MSHD Chunk: {decoded}")
    return decoded

def decode_MSPV_chunk(data):
    offset = 0
    decoded = []
    while offset < len(data):
        vertex, offset = decode_C3Vector_i(data, offset)
        decoded.append(vertex)
    logging.debug(f"MSPV Chunk: {decoded}")
    return decoded

def decode_MSPI_chunk(data):
    offset = 0
    decoded = []
    while offset < len(data):
        index, offset = decode_uint32(data, offset)
        decoded.append(index)
    logging.debug(f"MSPI Chunk: {decoded}")
    return decoded

def decode_MSCN_chunk(data):
    offset = 0
    decoded = []
    while offset < len(data):
        vector, offset = decode_C3Vector_i(data, offset)
        decoded.append(vector)
    logging.debug(f"MSCN Chunk: {decoded}")
    return decoded

def decode_MSLK_chunk(data):
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
    logging.debug(f"MSLK Chunk: {decoded}")
    return decoded

def decode_MSVT_chunk(data):
    offset = 0
    decoded = []
    while offset < len(data):
        vertex, offset = decode_C3Vector_i(data, offset)
        decoded.append(vertex)
    logging.debug(f"MSVT Chunk: {decoded}")
    return decoded

def decode_MSVI_chunk(data):
    offset = 0
    decoded = []
    while offset < len(data):
        index, offset = decode_uint32(data, offset)
        decoded.append(index)
    logging.debug(f"MSVI Chunk: {decoded}")
    return decoded

def decode_MSUR_chunk(data):
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
    logging.debug(f"MSUR Chunk: {decoded}")
    return decoded

def decode_IVSM_chunk(data):
    offset = 0
    decoded = []
    while offset < len(data):
        index, offset = decode_uint32(data, offset)
        decoded.append(index)
    logging.debug(f"IVSM Chunk: {decoded}")
    return decoded

def decode_LRPM_chunk(data):
    offset = 0
    decoded = []
    while offset < len(data):
        entry = {}
        entry['_0x00'], offset = decode_uint16(data, offset)
        entry['_0x02'], offset = decode_int16(data, offset)
        entry['_0x04'], offset = decode_uint16(data, offset)
        entry['_0x06'], offset = decode_uint16(data, offset)
        x, offset = decode_float(data, offset)
        z, offset = decode_float(data, offset)
        y, offset = decode_float(data, offset)  # Swapping y and z labels
        entry['position'] = {'x': x, 'y': y, 'z': z}
        entry['_0x14'], offset = decode_int16(data, offset)
        entry['_0x16'], offset = decode_uint16(data, offset)
        decoded.append(entry)
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

def decode_KLSM_chunk(data):
    offset = 0
    decoded = []
    while offset + 16 <= len(data):
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
    logging.debug(f"KLSM Chunk: {decoded}")
    return decoded

def decode_HBDM_chunk(data):
    offset = 0
    decoded = {}
    decoded['count'], offset = decode_uint32(data, offset)
    decoded['entries'] = []

    for _ in range(decoded['count']):
        entry = {}
        entry['index'] = []
        entry['filenames'] = []
        while offset < len(data):
            if offset + 8 > len(data):
                break
            sub_chunk_id = data[offset:offset+4].decode('utf-8')
            sub_chunk_size, offset = decode_uint32(data, offset + 4)
            if offset + sub_chunk_size > len(data):
                break
            sub_chunk_data = data[offset:offset+sub_chunk_size]
            if sub_chunk_id == 'IBDM':
                index, _ = decode_uint32(sub_chunk_data, 0)
                entry['index'].append(index)
            elif sub_chunk_id == 'FBDM':
                filenames = []
                sub_offset = 0
                while sub_offset < sub_chunk_size:
                    filename, sub_offset = decode_cstring(sub_chunk_data, sub_offset)
                    filenames.append(filename)
                entry['filenames'].extend(filenames)
            offset += sub_chunk_size
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

chunk_decoders = {
    'REVM': decode_MVER_chunk,
    'CRCM': decode_MCRC_chunk,
    'DHSM': decode_MSHD_chunk,
    'VPSM': decode_MSPV_chunk,
    'IPSM': decode_MSPI_chunk,
    'NCSM': decode_MSCN_chunk,
    'KLSM': decode_KLSM_chunk,
    'TVSM': decode_MSVT_chunk,
    'IVSM': decode_IVSM_chunk,
    'RUSM': decode_MSUR_chunk,
    'LRPM': decode_LRPM_chunk,
    'RRPM': decode_RRPM_chunk,
    'HBDM': decode_HBDM_chunk,
    'IBDM': decode_IBDM_chunk,
    'FBDM': decode_FBDM_chunk,
    'SODM': decode_SODM_chunk,
    'FSDM': decode_FSDM_chunk,
}
