# detailed_analysis.py
import json
import os
import logging
import argparse
from chunk_decoders import chunk_decoders

logging.basicConfig(level=logging.INFO)

def decode_chunks(input_json_path, output_json_path):
    with open(input_json_path, "r") as json_file:
        chunks = json.load(json_file)

    detailed_chunks = {}
    for chunk in chunks:
        chunk_id = chunk['id']
        chunk_data = bytes.fromhex(chunk['data'])
        if chunk_id in chunk_decoders:
            try:
                detailed_chunks[chunk_id] = chunk_decoders[chunk_id](chunk_data)
            except Exception as e:
                logging.error(f"Failed to decode chunk {chunk_id}: {e}")
                detailed_chunks[chunk_id] = {"error": str(e), "raw_data": chunk['data']}
        else:
            logging.warning(f"No decoder for chunk: {chunk_id}")
            detailed_chunks[chunk_id] = {"raw_data": chunk['data']}

    with open(output_json_path, "w") as json_file:
        json.dump(detailed_chunks, json_file, indent=4)

    logging.info(f"Saved detailed chunks to: {output_json_path}")

def main():
    parser = argparse.ArgumentParser(description="Decode chunks from initial analysis JSON.")
    parser.add_argument("input", help="Input JSON file path from initial analysis.")
    parser.add_argument("output", help="Output JSON file path for detailed analysis.")
    args = parser.parse_args()

    input_path = args.input
    output_path = args.output

    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    decode_chunks(input_path, output_path)

if __name__ == "__main__":
    main()
