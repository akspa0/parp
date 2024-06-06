import argparse
import os
import struct
import trimesh
from copy import deepcopy

# Mapping liquid types to human-readable strings
LIQUID_TYPE_MAPPING = {
    0: 'still',
    1: 'ocean',
    2: '?',
    3: 'slime',
    4: 'river',
    6: 'magma',
    8: 'fast flowing'
}

def parse_wlw_or_wlm_file(file_path, is_wlm=False, verbose=False):
    """
    Parses a WLW or WLM file and extracts informative data.
    """
    if verbose:
        print(f"Parsing file: {file_path}")
        
    with open(file_path, 'rb') as file:
        data = file.read()
        
        # Read header
        magic, version, unk06, liquid_type, padding, block_count = struct.unpack('4sHHHHI', data[:16])
        magic = magic.decode('utf-8')

        if is_wlm:
            liquid_type = 6  # For WLM files, liquidType is always 6 (Magma)

        result = {
            'magic': magic,
            'version': version,
            'unk06': unk06,
            'liquid_type': liquid_type,
            'liquid_type_str': LIQUID_TYPE_MAPPING.get(liquid_type, 'unknown'),
            'padding': padding,
            'block_count': block_count,
            'blocks': [],
            'block2_count': None,
            'blocks2': [],
            'unknown': None
        }

        offset = 16

        # Read blocks
        for _ in range(block_count):
            vertices = [struct.unpack('3f', data[offset + i*12 : offset + (i+1)*12]) for i in range(16)]
            offset += 48*4
            coord = struct.unpack('2f', data[offset:offset+2*4])
            offset += 2*4
            block_data = struct.unpack('80H', data[offset:offset+80*2])
            offset += 80*2
            result['blocks'].append({'vertices': vertices, 'coord': coord, 'data': block_data})

        # Read block2 if present
        if offset + 4 <= len(data):
            block2_count, = struct.unpack('I', data[offset:offset+4])
            offset += 4
            result['block2_count'] = block2_count

            for _ in range(block2_count):
                _unk00 = struct.unpack('3f', data[offset:offset+3*4])
                offset += 3*4
                _unk0C = struct.unpack('2f', data[offset:offset+2*4])
                offset += 2*4
                _unk14 = struct.unpack('56s', data[offset:offset+56])
                offset += 56
                result['blocks2'].append({'_unk00': _unk00, '_unk0C': _unk0C, '_unk14': _unk14})

        # Read unknown if version ≥ 1
        if version >= 1 and offset < len(data):
            unknown, = struct.unpack('B', data[offset:offset+1])
            result['unknown'] = unknown

    if verbose:
        print(f"Finished parsing file: {file_path}")
    
    return result

def generate_trimesh_obj_files(file_path, analysis_result, output_dir, relative_path, verbose=False):
    """
    Generates OBJ files using trimesh representing the heightmap from WLW/WLM file data.
    Generates an additional filled 3D object with added thickness.
    """
    if verbose:
        print(f"Generating OBJ files for: {file_path}")

    obj_output_dir = os.path.join(output_dir, relative_path)
    os.makedirs(obj_output_dir, exist_ok=True)
    
    vertices = []
    faces = []

    for block in analysis_result['blocks']:
        base_index = len(vertices)
        vertices.extend(block['vertices'])

        # Create faces using the grid structure
        for i in range(3):
            for j in range(3):
                v1 = base_index + i * 4 + j
                v2 = base_index + i * 4 + (j + 1)
                v3 = base_index + (i + 1) * 4 + (j + 1)
                v4 = base_index + (i + 1) * 4 + j
                faces.append([v1, v2, v3])
                faces.append([v1, v3, v4])

    # Create the original mesh
    original_mesh = trimesh.Trimesh(vertices=vertices, faces=faces)

    # Export the original mesh to OBJ file
    file_extension = '.wlw.obj' if file_path.endswith('.wlw') else '.wlm.obj'
    obj_filename = os.path.join(obj_output_dir, os.path.splitext(os.path.basename(file_path))[0] + file_extension)
    original_mesh.export(obj_filename)

    if verbose:
        print(f"Original OBJ file generated: {obj_filename}")

    # Create a filled 3D object by adding thickness
    thickness = 10.0  # Add 10 units of thickness
    top_vertices = deepcopy(vertices)
    bottom_vertices = [[v[0], v[1], v[2] - thickness] for v in vertices]
    filled_vertices = top_vertices + bottom_vertices

    # Create faces for the sides
    side_faces = []
    num_vertices = len(vertices)
    for i in range(num_vertices):
        next_i = (i + 1) % num_vertices
        side_faces.append([i, next_i, next_i + num_vertices])
        side_faces.append([i, next_i + num_vertices, i + num_vertices])

    # Create faces for the bottom
    bottom_faces = [[f[0] + num_vertices, f[2] + num_vertices, f[1] + num_vertices] for f in faces]

    # Combine all faces
    filled_faces = faces + bottom_faces + side_faces

    # Create the filled 3D mesh
    filled_mesh = trimesh.Trimesh(vertices=filled_vertices, faces=filled_faces)

    # Export the filled 3D mesh to OBJ file
    filled_obj_filename = os.path.join(obj_output_dir, '3d_' + os.path.splitext(os.path.basename(file_path))[0] + file_extension)
    filled_mesh.export(filled_obj_filename)

    if verbose:
        print(f"Filled 3D OBJ file generated: {filled_obj_filename}")

def analyze_files(input_directory, output_dir, verbose=False):
    """
    Analyzes WLW and WLM files in the input directory and prints informative data.
    Generates OBJ files for visualizing the heightmaps.
    """
    if verbose:
        print(f"Starting analysis of WLW and WLM files in directory: {input_directory}")
        
    for root, _, files in os.walk(input_directory):
        relative_root = os.path.relpath(root, input_directory)
        if verbose:
            print(f"Checking directory: {root} (relative: {relative_root})")
        
        folder_results = []
        for file in files:
            file_path = os.path.join(root, file)
            if verbose:
                print(f"Found file: {file_path}")
            if file.endswith('.wlw') or file.endswith('.wlm'):
                if verbose:
                    print(f"Processing {'WLM' if file.endswith('.wlm') else 'WLW'} file: {file_path}")
                is_wlm = file.endswith('.wlm')
                try:
                    analysis_result = parse_wlw_or_wlm_file(file_path, is_wlm, verbose)
                    folder_results.append((file_path, analysis_result, relative_root))
                except Exception as e:
                    print(f"Error processing file {file_path}: {e}")
                    continue
            else:
                if verbose:
                    print(f"Skipping non-WLW/WLM file: {file_path}")

        if not folder_results:
            if verbose:
                print(f"No WLW/WLM files found in directory: {root}")
            continue

        output_analysis_file = os.path.join(output_dir, f"{os.path.basename(root)}.txt")

        # Ensure the output directories exist
        os.makedirs(output_dir, exist_ok=True)

        if verbose:
            print(f"Writing analysis results to: {output_analysis_file}")

        with open(output_analysis_file, 'w') as f:
            for file_path, analysis_result, relative_root in folder_results:
                f.write(f"\nAnalyzing file: {file_path}\n")
                f.write(f"Liquid type: {analysis_result['liquid_type_str']} ({analysis_result['liquid_type']})\n")
                for key, value in analysis_result.items():
                    if key != 'blocks' and key != 'blocks2':
                        f.write(f"{key}: {value}\n")
                generate_trimesh_obj_files(file_path, analysis_result, output_dir, relative_root, verbose)

    if verbose:
        print("Analysis complete.")

def main():
    parser = argparse.ArgumentParser(description='Analyze WLW and WLM files in a directory and generate heightmap OBJ files.')
    parser.add_argument('input_directory', type=str, help='Directory containing WLW and WLM files to analyze')
    parser.add_argument('output_dir', type=str, help='Directory to save the generated analysis and OBJ files')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    args = parser.parse_args()

    analyze_files(args.input_directory, args.output_dir, args.verbose)

if __name__ == '__main__':
    main()
  
