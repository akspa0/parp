import os
import struct
import json
import logging
from datetime import datetime
from common_helpers import (
    decode_uint8, decode_uint16, decode_int16, decode_uint32, decode_float,
    decode_cstring, decode_C3Vector, decode_C3Vector_i, decode_RGBA, reverse_chunk_id
)
from extended_chunk_decoders import extended_chunk_decoders
from water_chunk_decoders import water_chunk_decoders
from sub_chunks_decoder import sub_chunk_decoders

# Configure logging
def setup_logging():
    log_folder = "logs"
    os.makedirs(log_folder, exist_ok=True)
    log_file = f"{log_folder}/adt_parser_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        filename=log_file,
        filemode='w',
        format='%(asctime)s [%(levelname)s] %(message)s',
        level=logging.DEBUG
    )
    logging.info(f"Logging setup complete. Log file: {log_file}")

# Save parsed data to JSON file
def save_parsed_data(data, output_file):
    output_folder = "parsed_data"
    os.makedirs(output_folder, exist_ok=True)
    with open(f"{output_folder}/{output_file}", 'w') as f:
        json.dump(data, f, indent=4)
    logging.info(f"Parsed data saved to {output_folder}/{output_file}")

# Combine all decoders into one dictionary
all_decoders = {}
all_decoders.update(extended_chunk_decoders)
all_decoders.update(water_chunk_decoders)
all_decoders.update(sub_chunk_decoders)

# Main Parsing Function
def parse_adt(file_path):
    """Parses an ADT file sequentially and decodes its chunks."""
    logging.info(f"Starting parsing for file: {file_path}")

    try:
        with open(file_path, 'rb') as file:
            data = file.read()
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        return

    offset = 0
    parsed_data = {
        'terrain': {},
        'metadata': {},
        'textures': {},
        'others': {}
    }

    while offset < len(data):
        try:
            chunk_id = data[offset:offset + 4].decode('utf-8', errors='ignore')
            chunk_size = struct.unpack_from('<I', data, offset + 4)[0]
            chunk_data = data[offset + 8:offset + 8 + chunk_size]
            offset += 8 + chunk_size

            chunk_id_reversed = reverse_chunk_id(chunk_id)
            decoder = all_decoders.get(chunk_id_reversed)
            if decoder:
                try:
                    decoded_data, _ = decoder(chunk_data)
                    if chunk_id.startswith('MC'):
                        parsed_data['terrain'][chunk_id] = decoded_data
                    elif chunk_id.startswith('MT') or chunk_id.startswith('MW'):
                        parsed_data['textures'][chunk_id] = decoded_data
                    elif chunk_id.startswith('MD') or chunk_id.startswith('MO'):
                        parsed_data['metadata'][chunk_id] = decoded_data
                    else:
                        parsed_data['others'][chunk_id] = decoded_data
                    logging.info(f"Decoded chunk {chunk_id_reversed} successfully.")
                except struct.error as e:
                    logging.error(f"Struct error in chunk {chunk_id_reversed} at offset {offset - chunk_size - 8}: {e}")
                except Exception as e:
                    logging.error(f"Error decoding chunk {chunk_id_reversed} at offset {offset - chunk_size - 8}: {e}")
            else:
                logging.warning(f"No decoder found for chunk {chunk_id_reversed} at offset {offset - chunk_size - 8}. Skipping.")

        except Exception as e:
            logging.error(f"General error processing chunk at offset {offset}: {e}")
            break

    output_file = file_path.split('/')[-1].replace('.adt', '_parsed.json')
    save_parsed_data(parsed_data, output_file)
    logging.info(f"Finished parsing file: {file_path}")
    return parsed_data

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python adt_analyzer.py <path_to_adt_file>")
        sys.exit(1)

    adt_file_path = sys.argv[1]
    setup_logging()
    parse_adt(adt_file_path)
