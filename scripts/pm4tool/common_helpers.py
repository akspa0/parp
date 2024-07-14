import os
import struct
import logging

def ensure_folder_exists(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)

def decode_uint8(data, offset):
    try:
        return data[offset], offset + 1
    except IndexError:
        logging.error("decode_uint8: Attempt to read beyond buffer size")
        return None, offset

def decode_uint16(data, offset):
    try:
        return struct.unpack_from('H', data, offset)[0], offset + 2
    except struct.error:
        logging.error("decode_uint16: Attempt to read beyond buffer size")
        return None, offset

def decode_int16(data, offset):
    try:
        return struct.unpack_from('h', data, offset)[0], offset + 2
    except struct.error:
        logging.error("decode_int16: Attempt to read beyond buffer size")
        return None, offset

def decode_uint32(data, offset):
    try:
        return struct.unpack_from('I', data, offset)[0], offset + 4
    except struct.error:
        logging.error("decode_uint32: Attempt to read beyond buffer size")
        return None, offset

def decode_float(data, offset):
    try:
        return struct.unpack_from('f', data, offset)[0], offset + 4
    except struct.error:
        logging.error("decode_float: Attempt to read beyond buffer size")
        return None, offset

def decode_cstring(data, offset, length):
    end = offset + length
    try:
        string_data = data[offset:end].decode('utf-8').rstrip('\0')
        return string_data, end
    except (struct.error, UnicodeDecodeError):
        logging.error("decode_cstring: Attempt to read beyond buffer size or decode error")
        return None, offset

def decode_C3Vector(data, offset):
    x, offset = decode_float(data, offset)
    y, offset = decode_float(data, offset)
    z, offset = decode_float(data, offset)
    return {'x': x, 'y': y, 'z': z}, offset

def decode_C3Vector_i(data, offset):
    x, offset = decode_int16(data, offset)
    y, offset = decode_int16(data, offset)
    z, offset = decode_int16(data, offset)
    return {'x': x, 'y': y, 'z': z}, offset

def decode_RGBA(data, offset):
    r, offset = decode_uint8(data, offset)
    g, offset = decode_uint8(data, offset)
    b, offset = decode_uint8(data, offset)
    a, offset = decode_uint8(data, offset)
    return {'r': r, 'g': g, 'b': b, 'a': a}, offset
