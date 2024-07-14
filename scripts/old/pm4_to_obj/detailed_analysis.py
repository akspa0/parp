import json
import logging
import argparse
from common_helpers import decode_uint8, decode_uint16, decode_int16, decode_uint32, decode_float, decode_cstring, decode_C3Vector, decode_C3Vector_i, decode_RGBA
from chunk_decoders import chunk_decoders

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')

def parse_chunks(json_data):
    parsed_data = {}
    hbdm_entries = []

    for chunk in json_data:
        chunk_id = chunk['id']
        chunk_data = bytearray(chunk['data'])  # Convert list of bytes back to bytearray
        if chunk_id == 'HBDM':
            hbdm_entries = chunk_decoders[chunk_id](chunk_data)['entries']
        elif chunk_id in chunk_decoders:
            if chunk_id not in parsed_data:
                parsed_data[chunk_id] = []
            parsed_data[chunk_id].append(chunk_decoders[chunk_id](chunk_data))
        else:
            logging.warning(f"No decoder found for chunk ID {chunk_id}")

    # Combine HBDM entries with IBDM and FBDM data
    if 'HBDM' in parsed_data:
        for entry in hbdm_entries:
            if entry['index'] is None and 'IBDM' in parsed_data:
                for ibdm_chunk in parsed_data['IBDM']:
                    entry['index'] = ibdm_chunk['m_destructible_building_index']
            if not entry['filenames'] and 'FBDM' in parsed_data:
                for fbdm_chunk in parsed_data['FBDM']:
                    entry['filenames'].extend(fbdm_chunk)
        parsed_data['HBDM'] = {'entries': hbdm_entries}

    return parsed_data

def main():
    parser = argparse.ArgumentParser(description="Parse chunks in a JSON file and output as detailed JSON.")
    parser.add_argument("input_json", type=str, help="Path to the input JSON file from initial analysis.")
    parser.add_argument("output_json", type=str, help="Path to the output detailed JSON file.")
    args = parser.parse_args()

    with open(args.input_json, 'r') as json_file:
        data = json.load(json_file)

    parsed_data = parse_chunks(data)

    with open(args.output_json, 'w') as output_json_file:
        json.dump(parsed_data, output_json_file, indent=4)

    logging.info(f"Output written to {args.output_json}")

if __name__ == "__main__":
    main()
