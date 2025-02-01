import struct
import json
import logging
from datetime import datetime
from common_helpers import ensure_folder_exists
from extended_chunk_decoders import extended_chunk_decoders
from water_chunk_decoders import water_chunk_decoders
from adt_chunk_decoders import adt_chunk_decoders
from sub_chunks_decoder import sub_chunk_decoders

# Configure logging
def setup_logging():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_folder = f"logs_{timestamp}"
    ensure_folder_exists(log_folder)
    
    log_file = f"{log_folder}/adt_parser_{timestamp}.log"
    logging.basicConfig(
        filename=log_file,
        filemode='w',
        format='%(asctime)s [%(levelname)s] %(message)s',
        level=logging.DEBUG
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger().addHandler(console)
    logging.info(f"Logging setup complete. Log file: {log_file}")

setup_logging()

# Combine all decoders into one dictionary
all_decoders = {}
all_decoders.update(adt_chunk_decoders)
all_decoders.update(sub_chunk_decoders)
all_decoders.update(extended_chunk_decoders)
all_decoders.update(water_chunk_decoders)

# Main parsing script
def reverse_chunk_id(chunk_id):
    """Reverse the chunk ID to handle reversed endianness."""
    return chunk_id[::-1]

def save_parsed_data(data, output_file):
    """Save parsed data to a JSON file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_folder = f"parsed_data_{timestamp}"
    ensure_folder_exists(output_folder)
    with open(f"{output_folder}/{output_file}", 'w') as f:
        json.dump(data, f, indent=4)
    logging.info(f"Parsed data saved to {output_folder}/{output_file}")

def parse_adt(file_path):
    """Parses an ADT file and decodes its chunks."""
    logging.info(f"Starting parsing for file: {file_path}")
    
    try:
        with open(file_path, 'rb') as file:
            data = file.read()
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        return

    offset = 0
    parsed_data = {}

    while offset < len(data):
        try:
            chunk_id = data[offset:offset + 4].decode('utf-8')
            chunk_id_reversed = reverse_chunk_id(chunk_id)
            chunk_size, offset = struct.unpack_from('<I', data, offset + 4)[0], offset + 8
            chunk_data = data[offset:offset + chunk_size]
            offset += chunk_size
        except (struct.error, UnicodeDecodeError) as e:
            logging.error(f"Error decoding chunk at offset {offset}: {e}")
            break

        logging.debug(f"Found chunk: {chunk_id_reversed} (original: {chunk_id}), size: {chunk_size}")

        if chunk_id_reversed in all_decoders:
            decoder = all_decoders[chunk_id_reversed]
            try:
                decoded_data, _ = decoder(chunk_data)
                if chunk_id_reversed not in parsed_data:
                    parsed_data[chunk_id_reversed] = []
                if chunk_id_reversed == 'MCNK':
                    parsed_data[chunk_id_reversed].append(decoded_data)
                else:
                    parsed_data[chunk_id_reversed].append(decoded_data)
                logging.info(f"Decoded chunk {chunk_id_reversed} successfully.")
            except Exception as e:
                logging.error(f"Error decoding chunk {chunk_id_reversed}: {e}")
        else:
            logging.warning(f"No decoder found for chunk {chunk_id_reversed}. Skipping.")

    output_file = file_path.split('/')[-1].replace('.adt', '_parsed.json')
    save_parsed_data(parsed_data, output_file)
    logging.info(f"Finished parsing file: {file_path}")
    return parsed_data

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python adt_parser.py <path_to_adt_file>")
        sys.exit(1)

    adt_file_path = sys.argv[1]
    parse_adt(adt_file_path)
