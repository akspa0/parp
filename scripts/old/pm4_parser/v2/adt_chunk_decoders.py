import logging
import struct
from common_helpers import (
    decode_uint32,
    decode_uint16,
    decode_C3Vector,
    decode_C3Vector_i
)

# Decoders for ADT chunks
def decode_MDDF(data, offset=0):
    entries = []
    while offset < len(data):
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
    while offset < len(data):
        entry = {}
        entry['nameId'], offset = decode_uint32(data, offset)
        entry['uniqueId'], offset = decode_uint32(data, offset)
        entry['position'], offset = decode_C3Vector_i(data, offset)
        entry['rotation'], offset = decode_C3Vector_i(data, offset)
        entry['lowerBounds'], offset = decode_C3Vector_i(data, offset)
        entry['upperBounds'], offset = decode_C3Vector_i(data, offset)
        entry['flags'], offset = decode_uint16(data, offset)
        entry['doodadSet'], offset = decode_uint16(data, offset)
        entry['nameSet'], offset = decode_uint16(data, offset)
        entry['scale'], offset = decode_uint16(data, offset)
        entries.append(entry)
    return {'entries': entries}

adt_chunk_decoders = {
    'FDDM': decode_MDDF,
    'FDOM': decode_MODF,
}

def parse_adt(file_path):
    with open(file_path, 'rb') as file:
        data = file.read()
    
    offset = 0
    parsed_data = {}
    while offset < len(data):
        chunk_id = data[offset:offset + 4].decode('utf-8')
        chunk_size = struct.unpack_from('<I', data, offset + 4)[0]
        chunk_data = data[offset + 8:offset + 8 + chunk_size]
        offset += 8 + chunk_size

        if chunk_id in adt_chunk_decoders:
            logging.debug(f"Decoding chunk: {chunk_id}, Size: {chunk_size}")
            parsed_data[chunk_id] = adt_chunk_decoders[chunk_id](chunk_data)
        else:
            logging.warning(f"No decoder found for chunk ID {chunk_id}")

    return parsed_data

if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser(description="Parse ADT files and extract FDDM and FDOM chunks.")
    parser.add_argument("adt_file", help="Input ADT file path.")
    parser.add_argument("output_file", help="Output file for the extracted data.")
    args = parser.parse_args()
    
    parsed_data = parse_adt(args.adt_file)
    with open(args.output_file, "w") as out_file:
        json.dump(parsed_data, out_file, indent=4)

    logging.info(f"Saved ADT chunk data to: {args.output_file}")
