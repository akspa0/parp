# detailed_parsing.py
import os
import json
import struct
import argparse
import logging
import sys

# Add the current directory to the sys.path to ensure we can import chunk_decoders
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from chunk_decoders import chunk_decoders

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def decode_chunks(input_json_path, output_json_path):
    logging.info(f"Decoding chunks from: {input_json_path}")
    with open(input_json_path, 'r') as json_file:
        chunks = json.load(json_file)
    
    detailed_chunks = {}
    for chunk_id, chunk in chunks.items():
        if "raw_data" in chunk:
            if chunk_id in chunk_decoders:
                try:
                    decoded_data = chunk_decoders[chunk_id](bytes.fromhex(chunk["raw_data"]))
                    detailed_chunks[chunk_id] = decoded_data
                except Exception as e:
                    logging.error(f"Error decoding chunk {chunk_id}: {e}")
                    detailed_chunks[chunk_id] = {
                        "error": str(e),
                        "raw_data": chunk["raw_data"]
                    }
            else:
                logging.warning(f"No decoder for chunk: {chunk_id}")
                detailed_chunks[chunk_id] = {
                    "raw_data": chunk["raw_data"]
                }
        else:
            detailed_chunks[chunk_id] = chunk["data"]
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    
    # Save detailed parsing to JSON file
    logging.info(f"Saving detailed chunks to: {output_json_path}")
    with open(output_json_path, 'w') as json_file:
        json.dump(detailed_chunks, json_file, indent=4)

def main():
    parser = argparse.ArgumentParser(description='Decode raw chunk data from initial analysis JSON files.')
    parser.add_argument('input', help='Input JSON file or directory containing initial analysis JSON files.')
    parser.add_argument('output', help='Output directory for detailed parsing JSON files.')
    
    args = parser.parse_args()
    
    input_path = args.input
    output_folder = args.output
    
    if os.path.isdir(input_path):
        for root, _, files in os.walk(input_path):
            for file in files:
                if file.endswith('_initial_analysis.json'):
                    input_json_path = os.path.join(root, file)
                    base_name = os.path.basename(file).replace('_initial_analysis.json', '')
                    output_json_path = os.path.join(output_folder, f"{base_name}_detailed_parsing.json")
                    decode_chunks(input_json_path, output_json_path)
    else:
        base_name = os.path.basename(input_path).replace('_initial_analysis.json', '')
        output_json_path = os.path.join(output_folder, f"{base_name}_detailed_parsing.json")
        decode_chunks(input_path, output_json_path)

if __name__ == "__main__":
    main()
