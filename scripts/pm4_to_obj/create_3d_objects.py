import argparse
import os
import json
import numpy as np
from PIL import Image
from scipy.interpolate import interp1d
import logging

# Set up logging
def setup_logging(output_directory, filename):
    log_file = os.path.join(output_directory, f"{filename}.log")
    logging.basicConfig(filename=log_file, level=logging.DEBUG, 
                        format='%(asctime)s %(levelname)s:%(message)s')

def ensure_folder_exists(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

def interpolate_normals(vertices, normals):
    vertex_count = len(vertices)
    normal_count = len(normals)

    if vertex_count == normal_count:
        return normals

    interp_func = interp1d(np.linspace(0, 1, normal_count), normals, axis=0, kind='linear')
    interpolated_normals = interp_func(np.linspace(0, 1, vertex_count))
    return interpolated_normals

def merge_vertices_and_normals(vertices, normals):
    merged_data = []
    for i in range(len(vertices)):
        merged_data.append(vertices[i].tolist() + normals[i].tolist())
    return np.array(merged_data)

def deduplicate_vertices_and_indices(vertices, indices):
    unique_vertices, inverse_indices = np.unique(vertices, axis=0, return_inverse=True)
    deduplicated_indices = inverse_indices[indices]
    return unique_vertices, deduplicated_indices

def generate_obj(vertices, indices, output_file):
    obj_data = []

    for vertex in vertices:
        if len(vertex) == 3:
            obj_data.append(f"v {vertex[0]} {vertex[1]} {vertex[2]}")
        elif len(vertex) == 6:
            obj_data.append(f"v {vertex[0]} {vertex[1]} {vertex[2]}")
            obj_data.append(f"vn {vertex[3]} {vertex[4]} {vertex[5]}")

    for face in indices:
        obj_data.append(f"f {' '.join([str(idx + 1) for idx in face])}")

    with open(output_file, 'w') as f:
        f.write("\n".join(obj_data))

def create_texture(colors, output_file):
    color_count = len(colors)
    texture_size = int(np.ceil(np.sqrt(color_count)))
    texture_data = np.zeros((texture_size, texture_size, 4), dtype=np.uint8)

    for i in range(color_count):
        x = i % texture_size
        y = i // texture_size
        texture_data[y, x] = colors[i]

    image = Image.fromarray(texture_data, 'RGBA')
    image.save(output_file)

def process_parsed_data(parsed_data, output_directory, filename_prefix):
    vertices = np.array(parsed_data.get('vertices', []))
    indices = np.array(parsed_data.get('indices', []))
    normals = np.array(parsed_data.get('normals', []))
    colors = parsed_data.get('colors', [])
    msvt = np.array(parsed_data.get('msvt', []))

    if len(vertices) > 0 and len(indices) > 0:
        if len(normals) > 0:
            interpolated_normals = interpolate_normals(vertices, normals)
            merged_vertices = merge_vertices_and_normals(vertices, interpolated_normals)
        else:
            merged_vertices = vertices

        unique_vertices, deduplicated_indices = deduplicate_vertices_and_indices(merged_vertices, indices)

        output_obj_file = os.path.join(output_directory, f"{filename_prefix}_combined.obj")
        generate_obj(unique_vertices, deduplicated_indices, output_obj_file)
        logging.info(f"3D object saved to {output_obj_file}")
    else:
        logging.warning("Insufficient vertex or index data for 3D object generation.")

    if len(colors) > 0:
        output_texture_file = os.path.join(output_directory, f"{filename_prefix}_texture.png")
        create_texture(colors, output_texture_file)
        logging.info(f"Texture saved to {output_texture_file}")
    else:
        logging.warning("No color data available for texture generation.")

    if len(msvt) > 0:
        output_msvt_file = os.path.join(output_directory, f"{filename_prefix}_msvt.obj")
        generate_obj(msvt, [], output_msvt_file)
        logging.info(f"MSVT 3D object saved to {output_msvt_file}")

def main():
    parser = argparse.ArgumentParser(description="Create 3D objects and textures from parsed PM4 data.")
    parser.add_argument("input_directory", type=str, help="Path to the directory containing parsed data JSON files.")
    parser.add_argument("output_directory", type=str, help="Folder to save the output files.")
    args = parser.parse_args()

    ensure_folder_exists(args.output_directory)

    for filename in os.listdir(args.input_directory):
        if filename.endswith("parsed_data.json"):
            input_file = os.path.join(args.input_directory, filename)
            with open(input_file, 'r') as f:
                parsed_data = json.load(f)

            filename_prefix = os.path.splitext(filename)[0]
            setup_logging(args.output_directory, filename_prefix)
            process_parsed_data(parsed_data, args.output_directory, filename_prefix)

if __name__ == "__main__":
    main()
