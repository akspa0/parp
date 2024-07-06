# pm4_parser.py
import argparse
import os
import struct
import json
import numpy as np

def parse_pm4_file(file_path):
    chunks = []
    with open(file_path, 'rb') as file:
        while True:
            header = file.read(8)
            if len(header) < 8:
                break
            chunk_id = header[:4].decode('utf-8')
            chunk_size = struct.unpack('I', header[4:8])[0]
            chunk_data = file.read(chunk_size)
            chunks.append((chunk_id, chunk_size, chunk_data))
    return chunks

def parse_vpos(data):
    vertices = struct.unpack(f'{len(data)//4}f', data)
    vertices = np.array(vertices).reshape(-1, 3)
    return vertices

def parse_indices(data):
    indices = struct.unpack(f'{len(data)//4}I', data)
    if len(indices) % 3 != 0:
        print(f"Warning: Indices array size {len(indices)} is not a multiple of 3. Trimming extra indices.")
        indices = indices[:len(indices) - (len(indices) % 3)]
    indices = np.array(indices).reshape(-1, 3)
    return indices

def parse_msvt(data):
    vertices = struct.unpack(f'{len(data)//4}f', data)
    vertices = np.array(vertices).reshape(-1, 3)
    world_positions = []
    for vertex in vertices:
        y, x, z = vertex
        world_y = 17066.666 - y
        world_x = 17066.666 - x
        world_z = z / 36.0
        world_positions.append([world_x, world_y, world_z])
    return world_positions

def parse_colors(data):
    num_colors = len(data) // 4
    colors = struct.unpack(f'{num_colors * 4}B', data)
    colors = np.array(colors).reshape(-1, 4)
    return colors

def parse_mprl(data):
    struct_format = 'HhHHfffH'
    entry_size = struct.calcsize(struct_format)
    num_entries = len(data) // entry_size
    mprl_entries = []

    for i in range(num_entries):
        entry_data = struct.unpack_from(struct_format, data, i * entry_size)
        position = entry_data[4:7]
        mprl_entries.append(position)

    return mprl_entries

def parse_generic_chunk(data):
    try:
        return np.frombuffer(data, dtype=np.float32).reshape(-1, 3).tolist()
    except ValueError as e:
        print(f"Failed to parse generic chunk: {e}")
        return []

def ensure_folder_exists(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

def main():
    parser = argparse.ArgumentParser(description="Parse PM4 files and save the data to a JSON file.")
    parser.add_argument("pm4_file", type=str, help="Path to the input PM4 file.")
    parser.add_argument("output_folder", type=str, help="Folder to save the output files.")
    args = parser.parse_args()

    ensure_folder_exists(args.output_folder)

    pm4_chunks = parse_pm4_file(args.pm4_file)

    parsed_data = {}

    for chunk_id, chunk_size, chunk_data in pm4_chunks:
        if chunk_id == 'VPSM':
            vertices = parse_vpos(chunk_data)
            parsed_data['vertices'] = vertices.tolist()
        elif chunk_id == 'IPSM':
            indices = parse_indices(chunk_data)
            parsed_data['indices'] = indices.tolist()
        elif chunk_id == 'NCSM':
            normals = parse_vpos(chunk_data)
            parsed_data['normals'] = normals.tolist()
        elif chunk_id == 'KLSM':
            colors = parse_colors(chunk_data)
            parsed_data['colors'] = colors.tolist()
        elif chunk_id == 'MSVT':
            world_positions = parse_msvt(chunk_data)
            parsed_data['msvt'] = world_positions
        elif chunk_id == 'MPRL':
            mprl_data = parse_mprl(chunk_data)
            parsed_data['mprl'] = mprl_data
        else:
            parsed_data[chunk_id] = parse_generic_chunk(chunk_data)

    output_json_file = os.path.join(args.output_folder, "parsed_data.json")
    with open(output_json_file, 'w') as f:
        json.dump(parsed_data, f, indent=4)

    print(f"Parsed information saved to {output_json_file}")

if __name__ == "__main__":
    main()
