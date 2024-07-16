import os
import json
import logging
import argparse
import time
from common_helpers import ensure_folder_exists, read_chunks_from_data, reverse_chunk_id
from wmo_chunk_decoders import decode_chunk

logging.basicConfig(filename=f'wmo_analysis_{time.strftime("%Y%m%d_%H%M%S")}.log', level=logging.INFO)

def analyze_wmo_file(file_path, output_dir):
    ensure_folder_exists(output_dir)
    with open(file_path, 'rb') as f:
        data = f.read()

    chunks = read_chunks_from_data(data)
    parsed_data = {}

    for chunk in chunks:
        chunk_id = chunk['id']
        chunk_data = chunk['data']
        reversed_chunk_id = reverse_chunk_id(chunk_id) if chunk_id not in chunk_decoders else chunk_id
        logging.info(f"Analyzing chunk: {chunk_id} (or {reversed_chunk_id})")
        parsed_chunk, _ = decode_chunk(reversed_chunk_id, chunk_data)
        parsed_data[chunk_id.decode('utf-8', errors='replace')] = parsed_chunk

    output_file = os.path.join(output_dir, f"{os.path.basename(file_path)}_data.json")
    with open(output_file, 'w') as f:
        json.dump(parsed_data, f, indent=4)

def main():
    parser = argparse.ArgumentParser(description="Analyze WMO files and output parsed data to JSON.")
    parser.add_argument("input_file", type=str, help="Path to the input WMO file.")
    parser.add_argument("output_dir", type=str, help="Directory to save the output JSON files.")
    args = parser.parse_args()

    analyze_wmo_file(args.input_file, args.output_dir)

if __name__ == "__main__":
    main()
