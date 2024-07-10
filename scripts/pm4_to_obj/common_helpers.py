import struct

# Helper functions for decoding
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
