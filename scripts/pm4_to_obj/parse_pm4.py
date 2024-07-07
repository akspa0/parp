import argparse
import os
import struct
import json
import numpy as np
import logging

# Set up logging
def setup_logging(output_directory, filename):
    log_file = os.path.join(output_directory, f"{filename}.log")
    logging.basicConfig(filename=log_file, level=logging.DEBUG, 
                        format='%(asctime)s %(levelname)s:%(message)s')

# Define common types parsing functions based on the wowdev.wiki Common_Types page
def parse_C3Vector(data):
    return struct.unpack('fff', data)

def parse_C3Vector_i(data):
    return struct.unpack('iii', data)

def parse_C2Vector(data):
    return struct.unpack('ff', data)

def parse_RGBA(data):
    return struct.unpack('BBBB', data)

# Other parsing functions remain the same
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
        logging.warning(f"Indices array size {len(indices)} is not a multiple of 3. Trimming extra indices.")
        indices = indices[:len(indices) - (len(indices) % 3)]
    indices = np.array(indices).reshape(-1, 3)
    return indices

def parse_msvt(data):
    num_vectors = len(data) // 12  # Each C3Vector is 12 bytes (3 * 4 bytes for floats)
    vertices = [parse_C3Vector(data[i*12:(i+1)*12]) for i in range(num_vectors)]
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
    colors = [parse_RGBA(data[i*4:(i+1)*4]) for i in range(num_colors)]
    return colors

def parse_mprl(data):
    struct_format = 'HhHHfffH'
    entry_size = struct.calcsize(struct_format)
    num_entries = len(data) // entry_size
    mprl_entries = []

    for i in range(num_entries):
        entry_data = struct.unpack_from(struct_format, data, i * entry_size)
        position = entry_data[4:7]
        mprl_entries.append({
            'unknown_1': entry_data[0],
            'unknown_2': entry_data[1],
            'unknown_3': entry_data[2],
            'unknown_4': entry_data[3],
            'position': position,
            'unknown_5': entry_data[7],
            'unknown_6': entry_data[8]
        })

    return mprl_entries

def parse_lrpm(data):
    entry_size = 24  # Each entry has 6 floats (24 bytes)
    num_entries = len(data) // entry_size
    lrpm_entries = []

    for i in range(num_entries):
        entry_data = struct.unpack_from('6f', data, i * entry_size)
        tilt_x_value = entry_data[1]
        tilt_y_value = entry_data[5]
        position_data = entry_data[2:5]
        lrpm_entries.append({
            'tilt_x': tilt_x_value,
            'tilt_y': tilt_y_value,
            'position_data': position_data
        })

    return lrpm_entries

def parse_generic_chunk(data):
    try:
        return np.frombuffer(data, dtype=np.float32).reshape(-1, 3).tolist()
    except ValueError as e:
        logging.error(f"Failed to parse generic chunk: {e}")
        return []

def ensure_folder_exists(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

def parse_pm4_file_to_json(file_path, output_directory):
    filename = os.path.basename(file_path)
    output_subfolder = os.path.join(output_directory, os.path.splitext(filename)[0])
    ensure_folder_exists(output_subfolder)

    # Set up logging for each file
    setup_logging(output_directory, os.path.splitext(filename)[0])

    pm4_chunks = parse_pm4_file(file_path)
    if not pm4_chunks:  # Skip files with no chunks
        logging.warning(f"Skipping {filename} as it contains no chunks.")
        return

    parsed_data = {}

    for chunk_id, chunk_size, chunk_data in pm4_chunks:
        try:
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
                parsed_data['colors'] = colors
            elif chunk_id == 'MSVT':
                world_positions = parse_msvt(chunk_data)
                parsed_data['msvt'] = world_positions
            elif chunk_id == 'MPRL':
                mprl_data = parse_mprl(chunk_data)
                parsed_data['mprl'] = mprl_data
            elif chunk_id == 'LRPM':
                lrpm_data = parse_lrpm(chunk_data)
                parsed_data['lrpm'] = lrpm_data
            else:
                parsed_data[chunk_id] = parse_generic_chunk(chunk_data)
        except Exception as e:
            logging.error(f"Error parsing chunk {chunk_id} in {filename}: {e}")

    if parsed_data:  # Only create folder and save JSON if there is parsed data
        output_json_file = os.path.join(output_subfolder, "parsed_data.json")
        with open(output_json_file, 'w') as f:
            json.dump(parsed_data, f, indent=4)
        logging.info(f"Parsed information for {filename} saved to {output_json_file}")
    else:
        logging.warning(f"No valid data found in {filename}. Skipping.")

def parse_pm4_directory(input_directory, output_directory):
    ensure_folder_exists(output_directory)

    for filename in os.listdir(input_directory):
        if filename.endswith(".pm4"):
            file_path = os.path.join(input_directory, filename)
            parse_pm4_file_to_json(file_path, output_directory)

def main():
    parser = argparse.ArgumentParser(description="Parse PM4 files and save the data to JSON files.")
    parser.add_argument("input_path", type=str, help="Path to the input PM4 file or directory containing PM4 files.")
    parser.add_argument("output_directory", type=str, help="Path to the output directory to save JSON files.")
    args = parser.parse_args()

    if os.path.isdir(args.input_path):
        parse_pm4_directory(args.input_path, args.output_directory)
    elif os.path.isfile(args.input_path) and args.input_path.endswith(".pm4"):
        parse_pm4_file_to_json(args.input_path, args.output_directory)
    else:
        print(f"Invalid input path: {args.input_path}. It should be a PM4 file or directory containing PM4 files.")

if __name__ == "__main__":
    main()
