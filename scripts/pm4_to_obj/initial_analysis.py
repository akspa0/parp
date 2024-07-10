import os
import json
import logging
import argparse

logging.basicConfig(level=logging.DEBUG)

def read_chunks(file_path):
    with open(file_path, "rb") as f:
        file_size = os.path.getsize(file_path)
        data = f.read()

    offset = 0
    chunks = []
    while offset < file_size:
        chunk_id = data[offset:offset+4].decode('utf-8')
        chunk_size = int.from_bytes(data[offset+4:offset+8], byteorder='little')
        chunk_data = data[offset+8:offset+8+chunk_size]
        chunks.append({
            'id': chunk_id,
            'size': chunk_size,
            'data': list(chunk_data)  # Store the chunk data as a list of bytes
        })
        logging.info(f"Read chunk: {chunk_id} (Size: {chunk_size})")
        offset += 8 + chunk_size

    return chunks

def main():
    parser = argparse.ArgumentParser(description="Parse and analyze PM4 files.")
    parser.add_argument("input", help="Input PM4 file path.")
    parser.add_argument("output", help="Output directory for JSON files.")
    args = parser.parse_args()

    input_path = args.input
    output_dir = args.output

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    chunks = read_chunks(input_path)
    output_path = os.path.join(output_dir, os.path.basename(input_path) + "_initial_analysis.json")

    with open(output_path, "w") as out_file:
        json.dump(chunks, out_file, indent=4)

    logging.info(f"Saved initial analysis to: {output_path}")

if __name__ == "__main__":
    main()
