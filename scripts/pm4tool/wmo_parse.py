import os
import argparse
import json
import logging
import time

def ensure_folder_exists(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

def parse_movt(data):
    num_vertices = len(data) // 12
    vertices = []
    for i in range(num_vertices):
        x = int.from_bytes(data[i*12:i*12+4], 'little') / 36.0
        y = int.from_bytes(data[i*12+4:i*12+8], 'little') / 36.0
        z = int.from_bytes(data[i*12+8:i*12+12], 'little') / 36.0
        vertices.append((x, y, z))
    return vertices

def parse_movi(data):
    num_indices = len(data) // 2
    indices = []
    for i in range(num_indices):
        idx = int.from_bytes(data[i*2:i*2+2], 'little')
        indices.append(idx)
    return indices

def parse_monr(data):
    num_normals = len(data) // 12
    normals = []
    for i in range(num_normals):
        x = int.from_bytes(data[i*12:i*12+4], 'little') / 36.0
        y = int.from_bytes(data[i*12+4:i*12+8], 'little') / 36.0
        z = int.from_bytes(data[i*12+8:i*12+12], 'little') / 36.0
        normals.append((x, y, z))
    return normals

def parse_chunk(chunk_id, data):
    if chunk_id == 'MOVT':
        return parse_movt(data)
    elif chunk_id == 'MOVI':
        return parse_movi(data)
    elif chunk_id == 'MONR':
        return parse_monr(data)
    else:
        return data.hex()  # Convert bytes to hex string for non-parsed chunks

def read_chunks(file_path):
    chunks = {}
    with open(file_path, 'rb') as f:
        while True:
            chunk_header = f.read(8)
            if len(chunk_header) < 8:
                break
            chunk_id = chunk_header[:4].decode('ascii')
            chunk_size = int.from_bytes(chunk_header[4:], 'little')
            chunk_data = f.read(chunk_size)
            chunks[chunk_id] = chunk_data
    return chunks

def analyze_wmo_file(file_path, output_dir):
    logging.info(f"Processing WMO file: {file_path}")
    chunks = read_chunks(file_path)
    parsed_data = {chunk_id: parse_chunk(chunk_id, data) for chunk_id, data in chunks.items()}
    output_file = os.path.join(output_dir, os.path.splitext(os.path.basename(file_path))[0] + '_data.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(parsed_data, f, indent=4)
    logging.info(f"Saved extracted data to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Parse WMO files.")
    parser.add_argument('input_dir', help="Directory containing WMO files.")
    parser.add_argument('output_dir', help="Directory to save the parsed data.")
    args = parser.parse_args()

    ensure_folder_exists(args.output_dir)

    log_file = os.path.join(args.output_dir, f"wmo_analysis_{time.strftime('%Y%m%d_%H%M%S')}.log")
    logging.basicConfig(filename=log_file, level=logging.INFO)

    for file_name in os.listdir(args.input_dir):
        if file_name.endswith('.wmo'):
            file_path = os.path.join(args.input_dir, file_name)
            analyze_wmo_file(file_path, args.output_dir)

if __name__ == "__main__":
    main()
