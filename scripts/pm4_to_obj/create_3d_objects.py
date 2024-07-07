import argparse
import os
import json
import numpy as np
from PIL import Image
from scipy.interpolate import interp1d

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
    deduplicated_indices = inverse_indices[indices].reshape(-1, 3)
    return unique_vertices, deduplicated_indices

def generate_obj(vertices, indices, filename, include_normals=False):
    obj_data = []

    for vertex in vertices:
        if include_normals:
            if len(vertex) == 6:  # Ensure there are normals to include
                obj_data.append(f"v {vertex[0]} {vertex[1]} {vertex[2]}\nvn {vertex[3]} {vertex[4]} {vertex[5]}")
            else:
                obj_data.append(f"v {vertex[0]} {vertex[1]} {vertex[2]}")
        else:
            obj_data.append(f"v {vertex[0]} {vertex[1]} {vertex[2]}")

    for face in indices:
        if include_normals:
            obj_data.append(f"f {face[0]+1}//{face[0]+1} {face[1]+1}//{face[1]+1} {face[2]+1}//{face[2]+1}")
        else:
            obj_data.append(f"f {face[0]+1} {face[1]+1} {face[2]+1}")

    with open(filename, 'w') as f:
        f.write("\n".join(obj_data))
    print(f"3D object saved to {filename}")

def create_texture(colors, output_file):
    num_colors = len(colors)
    size = int(np.ceil(np.sqrt(num_colors)))

    if size % 16 != 0:
        size = (size // 16 + 1) * 16  # Ensure the size is a multiple of 16

    image = Image.new('RGBA', (size, size))
    pixels = image.load()

    for i, color in enumerate(colors):
        x = i % size
        y = i // size
        if y < size:
            pixels[x, y] = tuple(color)

    image.save(output_file)
    print(f"Texture saved to {output_file}")

def interpolate_vertices(vertices, target_length):
    current_length = len(vertices)
    if current_length == 0:
        print("Warning: No vertices to interpolate.")
        return vertices  # Return empty if no vertices are present
    elif current_length == 1:
        # Replicate single vertex to match target length
        interpolated_vertices = np.tile(vertices, (target_length, 1))
    elif current_length >= target_length:
        return vertices
    else:
        interp_func = interp1d(np.linspace(0, 1, current_length), vertices, axis=0, kind='linear')
        interpolated_vertices = interp_func(np.linspace(0, 1, target_length))
    return interpolated_vertices

def validate_chunk_data(chunk_id, vertices):
    if vertices.size % 3 != 0:
        print(f"Skipping chunk {chunk_id} due to incompatible vertex array size {vertices.size}")
        return False
    return True

def process_additional_chunks(parsed_data, output_folder, prefix):
    for chunk_id, chunk_data in parsed_data.items():
        if chunk_id not in ['vertices', 'indices', 'normals', 'colors', 'msvt', 'mprl']:
            vertices = np.array(chunk_data)
            if not validate_chunk_data(chunk_id, vertices):
                continue
            vertices = vertices.reshape(-1, 3)
            if len(vertices) < 3:
                print(f"Interpolating vertices for chunk {chunk_id} due to insufficient data")
                vertices = interpolate_vertices(vertices, 3)
            if len(vertices) < 3:
                print(f"Skipping chunk {chunk_id} due to insufficient vertices after interpolation")
                continue
            indices = np.arange(len(vertices))
            if len(indices) % 3 != 0:
                print(f"Skipping chunk {chunk_id} due to incompatible index array size {len(indices)}")
                continue
            indices = indices.reshape(-1, 3)
            filename = os.path.join(output_folder, f"{prefix}_{chunk_id}_layer.obj")
            generate_obj(vertices, indices, filename, include_normals=False)

def process_parsed_directory(input_directory, output_directory):
    ensure_folder_exists(output_directory)

    for foldername in os.listdir(input_directory):
        folder_path = os.path.join(input_directory, foldername)
        if os.path.isdir(folder_path):
            parsed_data_file = os.path.join(folder_path, "parsed_data.json")
            if os.path.exists(parsed_data_file):
                output_subfolder = os.path.join(output_directory, foldername)
                ensure_folder_exists(output_subfolder)
                with open(parsed_data_file, 'r') as f:
                    parsed_data = json.load(f)

                prefix = os.path.splitext(foldername)[0]

                if 'vertices' in parsed_data and 'normals' in parsed_data and 'indices' in parsed_data:
                    vertices = np.array(parsed_data['vertices'])
                    normals = np.array(parsed_data['normals'])
                    indices = np.array(parsed_data['indices'])

                    normals = interpolate_normals(vertices, normals)
                    combined_vertices = merge_vertices_and_normals(vertices, normals)
                    unique_vertices, deduplicated_indices = deduplicate_vertices_and_indices(combined_vertices, indices)
                    generate_obj(unique_vertices, deduplicated_indices, os.path.join(output_subfolder, f"{prefix}_combined_layer.obj"), include_normals=True)

                if 'colors' in parsed_data:
                    create_texture(parsed_data['colors'], os.path.join(output_subfolder, f"{prefix}_texture.png"))

                if 'msvt' in parsed_data:
                    msvt_vertices = np.array(parsed_data['msvt']).reshape(-1, 3)
                    if len(msvt_vertices) < 3:
                        print("Interpolating MSVT vertices due to insufficient data")
                        msvt_vertices = interpolate_vertices(msvt_vertices, 3)
                    if len(msvt_vertices) < 3:
                        print("Skipping MSVT layer due to insufficient vertices after interpolation")
                    else:
                        msvt_indices = np.arange(len(msvt_vertices)).reshape(-1, 3)
                        generate_obj(msvt_vertices, msvt_indices, os.path.join(output_subfolder, f"{prefix}_msvt_layer.obj"), include_normals=False)

                if 'mprl' in parsed_data:
                    mprl_vertices = np.array(parsed_data['mprl']).reshape(-1, 3)
                    if len(mprl_vertices) < 3:
                        print("Interpolating MPRL vertices due to insufficient data")
                        mprl_vertices = interpolate_vertices(mprl_vertices, 3)
                    if len(mprl_vertices) < 3:
                        print("Skipping MPRL layer due to insufficient vertices after interpolation")
                    else:
                        mprl_indices = np.arange(len(mprl_vertices)).reshape(-1, 3)
                        generate_obj(mprl_vertices, mprl_indices, os.path.join(output_subfolder, f"{prefix}_mprl_layer.obj"), include_normals=False)

                # Process additional chunks and create separate OBJ files if they contain vertex data
                process_additional_chunks(parsed_data, output_subfolder, prefix)

def main():
    parser = argparse.ArgumentParser(description="Create 3D objects and textures from parsed PM4 data.")
    parser.add_argument("input_directory", type=str, help="Path to the directory containing parsed data JSON files.")
    parser.add_argument("output_directory", type=str, help="Folder to save the output files.")
    args = parser.parse_args()

    process_parsed_directory(args.input_directory, args.output_directory)

if __name__ == "__main__":
    main()
