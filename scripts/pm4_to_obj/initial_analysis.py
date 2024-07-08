# initial_analysis.py
import os
import struct
import json
import logging
import argparse

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def read_chunk(file):
    chunk_id = file.read(4).decode('utf-8')
    chunk_size = struct.unpack('I', file.read(4))[0]
    chunk_data = file.read(chunk_size)
    return chunk_id, chunk_size, chunk_data

def read_chunks(file_path):
    chunks = {}
    logging.info(f"Reading file: {file_path}")
    
    with open(file_path, 'rb') as f:
        while True:
            if f.tell() == os.fstat(f.fileno()).st_size:
                break
            chunk_id, chunk_size, chunk_data = read_chunk(f)
            chunks[chunk_id] = {
                "size": chunk_size,
                "raw_data": chunk_data.hex()
            }
            logging.info(f"Read chunk: {chunk_id} (Size: {chunk_size})")
    
    return chunks

def process_file(file_path, output_folder):
    # Stage 1: Initial Analysis
    chunks = read_chunks(file_path)
    
    # Create output subfolder
    base_name = os.path.basename(file_path)
    name, _ = os.path.splitext(base_name)
    output_subfolder = os.path.join(output_folder, name)
    os.makedirs(output_subfolder, exist_ok=True)
    
    # Save initial analysis to JSON file
    initial_json_path = os.path.join(output_subfolder, f"{name}_initial_analysis.json")
    with open(initial_json_path, 'w') as json_file:
        json.dump(chunks, json_file, indent=4)

def main():
    parser = argparse.ArgumentParser(description='Parse PM4 and ADT files and output raw chunk data in JSON files.')
    parser.add_argument('input', help='Input file or directory containing PM4 or ADT files.')
    parser.add_argument('output', help='Output directory for JSON files.')
    
    args = parser.parse_args()
    
    input_path = args.input
    output_folder = args.output
    
    if os.path.isdir(input_path):
        for root, _, files in os.walk(input_path):
            for file in files:
                if file.endswith('.pm4') or file.endswith('.adt'):
                    process_file(os.path.join(root, file), output_folder)
    else:
        process_file(input_path, output_folder)

if __name__ == "__main__":
    main()
