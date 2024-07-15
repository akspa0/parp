import struct
from common_helpers import decode_uint32, decode_float, decode_C3Vector, decode_int16, decode_cstring, decode_RGBA

# Function to decode REVM chunk
def decode_REVM(data):
    version, _ = decode_uint32(data, 0)
    return {"version": version}

# Function to decode DHOM chunk
def decode_DHOM(data):
    offset = 0
    values = []
    for _ in range(16):
        value, offset = decode_uint32(data, offset)
        values.append(value)
    return {"values": values}

# Function to decode TMOM chunk
def decode_TMOM(data):
    offset = 0
    values = []
    for _ in range(64):
        value, offset = decode_uint32(data, offset)
        values.append(value)
    return {"values": values}

# Function to decode NGOM chunk
def decode_NGOM(data):
    name, _ = decode_cstring(data, 0, 12)
    return {"name": name}

# Function to decode IGOM chunk
def decode_IGOM(data):
    offset = 0
    values = []
    for _ in range(8):
        value, offset = decode_uint32(data, offset)
        values.append(value)
    return {"values": values}

# Function to decode BSOM chunk
def decode_BSOM(data):
    value, _ = decode_uint32(data, 0)
    return {"value": value}

# Function to decode SDOM chunk
def decode_SDOM(data):
    offset = 0
    values = []
    while offset < len(data):
        value, offset = decode_cstring(data, offset, 32)
        values.append(value)
    return {"values": values}

# Function to decode DDOM chunk
def decode_DDOM(data):
    offset = 0
    values = []
    for _ in range(20):
        value, offset = decode_float(data, offset)
        values.append(value)
    return {"values": values}

# Function to decode GOFM chunk
def decode_GOFM(data):
    offset = 0
    values = []
    for _ in range(12):
        value, offset = decode_uint32(data, offset)
        values.append(value)
    return {"values": values}

# Function to decode DIFG chunk
def decode_DIFG(data):
    value, _ = decode_uint32(data, 0)
    return {"value": value}

# Function to decode IDOM chunk
def decode_IDOM(data):
    offset = 0
    values = []
    for _ in range(3):
        value, offset = decode_uint32(data, offset)
        values.append(value)
    return {"values": values}

# Function to decode PGOM chunk
def decode_PGOM(data):
    offset = 0
    values = []
    for _ in range(7740):
        value, offset = decode_uint32(data, offset)
        values.append(value)
    return {"values": values}

# Dictionary mapping chunk IDs to their decoder functions
chunk_decoders = {
    'REVM': decode_REVM,
    'MVER': decode_REVM,
    'DHOM': decode_DHOM,
    'MHOD': decode_DHOM,
    'TMOM': decode_TMOM,
    'MOTM': decode_TMOM,
    'NGOM': decode_NGOM,
    'MOGN': decode_NGOM,
    'IGOM': decode_IGOM,
    'MOGI': decode_IGOM,
    'BSOM': decode_BSOM,
    'MOSB': decode_BSOM,
    'SDOM': decode_SDOM,
    'MODS': decode_SDOM,
    'DDOM': decode_DDOM,
    'MODD': decode_DDOM,
    'GOFM': decode_GOFM,
    'MFOG': decode_GOFM,
    'DIFG': decode_DIFG,
    'GFID': decode_DIFG,
    'IDOM': decode_IDOM,
    'MODI': decode_IDOM,
    'PGOM': decode_PGOM,
    'MOGP': decode_PGOM
}

# Function to decode a chunk based on its ID
def decode_chunk(chunk_id, data):
    decoder = chunk_decoders.get(chunk_id)
    if decoder:
        return decoder(data)
    else:
        return {"unknown_chunk": data.hex()}

# Function to process a WMO file and decode all chunks
def process_wmo_file(file_path):
    with open(file_path, 'rb') as f:
        data = f.read()

    offset = 0
    chunks = []
    while offset < len(data):
        chunk_id = data[offset:offset + 4][::-1].decode('utf-8')  # Reverse bytes and decode
        chunk_size = struct.unpack('I', data[offset + 4:offset + 8])[0]
        chunk_data = data[offset + 8:offset + 8 + chunk_size]
        decoded_chunk = decode_chunk(chunk_id, chunk_data)
        chunks.append({chunk_id: decoded_chunk})
        offset += 8 + chunk_size

    return chunks
