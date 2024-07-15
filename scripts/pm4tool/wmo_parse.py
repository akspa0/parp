import struct
import os
import json
import logging
import argparse

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')

def ensure_folder_exists(folder_path):
    if folder_path and not os.path.exists(folder_path):
        os.makedirs(folder_path)

def read_chunks(file_path):
    with open(file_path, "rb") as f:
        file_size = os.path.getsize(file_path)
        data = f.read()

    offset = 0
    chunks = []
    while offset < file_size:
        chunk_id = data[offset:offset+4]
        try:
            chunk_id_str = chunk_id.decode('utf-8')
        except UnicodeDecodeError:
            logging.error(f"Failed to decode chunk ID at offset {offset}. Skipping this chunk.")
            offset += 4
            continue
        
        chunk_size = int.from_bytes(data[offset+4:offset+8], byteorder='little')
        chunk_data = data[offset+8:offset+8+chunk_size]
        chunks.append({
            'id': chunk_id_str,
            'size': chunk_size,
            'data': chunk_data
        })
        logging.info(f"Read chunk: {chunk_id_str} (Size: {chunk_size})")
        offset += 8 + chunk_size

    return chunks

def reverse_chunk_id(chunk_id):
    return chunk_id[::-1]

def parse_vertices(chunk):
    count = len(chunk['data']) // 12
    vertices = struct.unpack_from('<' + 'fff' * count, chunk['data'])
    return [{"x": vertices[i], "y": vertices[i + 1], "z": vertices[i + 2]} for i in range(0, len(vertices), 3)]

def parse_indices(chunk):
    count = len(chunk['data']) // 2
    indices = struct.unpack_from('<' + 'H' * count, chunk['data'])
    return list(indices)

def parse_normals(chunk):
    count = len(chunk['data']) // 12
    normals = struct.unpack_from('<' + 'fff' * count, chunk['data'])
    return [{"nx": normals[i], "ny": normals[i + 1], "nz": normals[i + 2]} for i in range(0, len(normals), 3)]

def extract_wmo_root_data(chunks):
    vertices = []
    faces = []
    normals = []
    
    for chunk in chunks:
        chunk_id = chunk['id']
        reverse_id = reverse_chunk_id(chunk_id)
        logging.info(f"Analyzing chunk: {chunk_id} (or {reverse_id})")
        if chunk_id == 'MOVT' or reverse_id == 'MOVT':
            vertices = parse_vertices(chunk)
        elif chunk_id == 'MOVI' or reverse_id == 'MOVI':
            faces = parse_indices(chunk)
        elif chunk_id == 'MONR' or reverse_id == 'MONR':
            normals = parse_normals(chunk)
        else:
            logging.info(f"Chunk {chunk_id} is not identified for vertices, faces, or normals")

    return {
        "vertices": vertices,
        "faces": faces,
        "normals": normals
}

def extract_wmo_group_data(chunks):
    vertices = []
    faces = []
    normals = []
    
    for chunk in chunks:
        chunk_id = chunk['id']
        reverse_id = reverse_chunk_id(chunk_id)
        logging.info(f"Analyzing chunk: {chunk_id} (or {reverse_id})")
        if chunk_id == 'MOGP' or reverse_id == 'MOGP':
            sub_chunks = read_chunks_from_data(chunk['data'])
            for sub_chunk in sub_chunks:
                sub_chunk_id = sub_chunk['id']
                sub_reverse_id = reverse_chunk_id(sub_chunk_id)
                if sub_chunk_id == 'MOVT' or sub_reverse_id == 'MOVT':
                    vertices = parse_vertices(sub_chunk)
                elif sub_chunk_id == 'MOVI' or sub_reverse_id == 'MOVI':
                    faces = parse_indices(sub_chunk)
                elif sub_chunk_id == 'MONR' or sub_reverse_id == 'MONR':
                    normals = parse_normals(sub_chunk)
        else:
            logging.info(f"Chunk {chunk_id} is not identified for vertices, faces, or normals")

    return {
        "vertices": vertices,
        "faces": faces,
        "normals": normals
}

def read_chunks_from_data(data):
    offset = 0
    data_size = len(data)
    chunks = []
    while offset < data_size:
        chunk_id = data[offset:offset+4]
        try:
            chunk_id_str = chunk_id.decode('utf-8')
        except UnicodeDecodeError:
            logging.error(f"Failed to decode chunk ID at offset {offset}. Skipping this chunk.")
            offset += 4
            continue
        
        chunk_size = int.from_bytes(data[offset+4:offset+8], byteorder='little')
        chunk_data = data[offset+8:offset+8+chunk_size]
        chunks.append({
            'id': chunk_id_str,
            'size': chunk_size,
            'data': chunk_data
        })
        offset += 8 + chunk_size
    return chunks

def save_extracted_data(data, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def main():
    parser = argparse.ArgumentParser(description="Extract data from WMO files.")
    parser.add_argument("input_dir", type=str, help="Path to the input directory containing WMO files.")
    parser.add_argument("output_dir", type=str, help="Path to the output directory to save extracted data.")
    args = parser.parse_args()

    ensure_folder_exists(args.output_dir)

    wmo_files = [os.path.join(args.input_dir, f) for f in os.listdir(args.input_dir) if f.endswith('.wmo')]

    for wmo_file in wmo_files:
        chunks = read_chunks(wmo_file)
        if '_000.wmo' in wmo_file or '_001.wmo' in wmo_file:
            data = extract_wmo_group_data(chunks)
        else:
            data = extract_wmo_root_data(chunks)
        
        output_file = os.path.join(args.output_dir, os.path.splitext(os.path.basename(wmo_file))[0] + "_data.json")
        save_extracted_data(data, output_file)
        logging.info(f"Saved extracted data to {output_file}")

if __name__ == "__main__":
    main()
