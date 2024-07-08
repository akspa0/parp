import argparse
import os
import json
import logging
from chunk_decoders import chunk_decoders

def load_json(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

def save_json(data, filepath):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def decode_chunks(input_json_path, output_json_path):
    data = load_json(input_json_path)
    detailed_chunks = {}

    for chunk in data:
        chunk_id = chunk['id']
        chunk_data = bytes.fromhex(chunk['data'])

        if chunk_id in chunk_decoders:
            try:
                decoded_data = chunk_decoders[chunk_id](chunk_data)
                detailed_chunks[chunk_id] = decoded_data
            except Exception as e:
                logging.error(f"Error decoding chunk {chunk_id}: {e}")
                detailed_chunks[chunk_id] = {
                    "error": str(e),
                    "raw_data": chunk['data']
                }
        else:
            logging.warning(f"No decoder for chunk: {chunk_id}")
            detailed_chunks[chunk_id] = {
                "raw_data": chunk['data']
            }

    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    save_json(detailed_chunks, output_json_path)
    logging.info(f"Saved detailed chunks to: {output_json_path}")

def main():
    parser = argparse.ArgumentParser(description="Detailed analysis of PM4 file.")
    parser.add_argument("input_json", help="Path to the input JSON file from initial analysis.")
    parser.add_argument("output_folder", help="Folder to save the detailed analysis.")
    args = parser.parse_args()

    input_path = args.input_json
    output_json_path = os.path.join(args.output_folder, os.path.basename(input_path).replace('_initial_analysis.json', '_detailed_parsing.json'))
    decode_chunks(input_path, output_json_path)

if __name__ == "__main__":
    main()
