import argparse
import os
import struct
from stl import mesh
from collections import defaultdict

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
            if offset + 48*4 + 2*4 + 80*2 > len(data):
                break
            try:
                vertices = [struct.unpack('3f', data[offset + i*12 : offset + (i+1)*12]) for i in range(16)]
                offset += 48*4
                coord = struct.unpack('2f', data[offset:offset+2*4])
                offset += 2*4
                block_data = struct.unpack('80H', data[offset:offset+80*2])
                offset += 80*2
                result['blocks'].append({'vertices': vertices, 'coord': coord, 'data': block_data})
            except struct.error as e:
                print(f"Error unpacking block at offset {offset}: {e}")
                break
            if offset >= len(data):
                break

        # Read block2 if present
        if offset + 4 <= len(data):
            block2_count, = struct.unpack('I', data[offset:offset+4])
            offset += 4
            result['block2_count'] = block2_count

            for _ in range(block2_count):
                if offset + 3*4 + 2*4 + 56 > len(data):
                    break
                try:
                    _unk00 = struct.unpack('3f', data[offset:offset+3*4])
                    offset += 3*4
                    _unk0C = struct.unpack('2f', data[offset:offset+2*4])
                    offset += 2*4
                    _unk14 = struct.unpack('56s', data[offset:offset+56])
                    offset += 56
                    result['blocks2'].append({'_unk00': _unk00, '_unk0C': _unk0C, '_unk14': _unk14})
                except struct.error as e:
                    print(f"Error unpacking block2 at offset {offset}: {e}")
                    break

        # Read unknown if version ≥ 1
        if version >= 1 and offset < len(data):
            unknown, = struct.unpack('B', data[offset:offset+1])
            result['unknown'] = unknown

    if verbose:
        print(f"Finished parsing file: {file_path}")
    
    return result

def generate_combined_stl_file(file_path, analysis_result, output_dir, relative_path, verbose=False):
    """
    Generates a combined STL file representing the heightmap from all blocks in a WLW/WLM file.
    """
    if verbose:
        print(f"Generating combined STL file for: {file_path}")

    obj_output_dir = os.path.join(output_dir, relative_path)
    os.makedirs(obj_output_dir, exist_ok=True)
    
    vertices = []
    faces = []
    base_index = 0

    for block in analysis_result['blocks']:
        block_vertices = block['vertices']
        vertices.extend(block_vertices)

        # Create faces using the grid structure
        for i in range(3):
            for j in range(3):
                v1 = base_index + i * 4 + j
                v2 = base_index + i * 4 + (j + 1)
                v3 = base_index + (i + 1) * 4 + (j + 1)
                v4 = base_index + (i + 1) * 4 + j
                faces.append([v1, v2, v3])
                faces.append([v1, v3, v4])
        
        base_index += len(block_vertices)

    vertices = np.array(vertices)
    faces = np.array(faces)
    
    combined_mesh = mesh.Mesh(np.zeros(faces.shape[0], dtype=mesh.Mesh.dtype))
    for i, face in enumerate(faces):
        for j in range(3):
            combined_mesh.vectors[i][j] = vertices[face[j]]

    stl_filename = os.path.join(obj_output_dir, os.path.splitext(os.path.basename(file_path))[0] + '.stl')
    combined_mesh.save(stl_filename)

    if verbose:
        print(f"Combined STL file generated: {stl_filename}")

def analyze_files(input_directory, output_dir, verbose=False):
    """
    Analyzes WLW and WLM files in the input directory and prints informative data.
    Generates combined STL files for visualizing the heightmaps.
    """
    if verbose:
        print(f"Starting analysis of WLW and WLM files in directory: {input_directory}")
        
    for root, _, files in os.walk(input_directory):
        relative_root = os.path.relpath(root, input_directory)
        if verbose:
            print(f"Checking directory: {root} (relative: {relative_root})")
        
        for file in files:
            file_path = os.path.join(root, file)
            if verbose:
                print(f"Found file: {file_path}")
            if file.endswith('.wlw') or file.endswith('.wlm') or file.endswith('.wlw.not') or file.endswith('.wlm.not'):
                if verbose:
                    print(f"Processing {'WLM' if file.endswith('.wlm') or file.endswith('.wlm.not') else 'WLW'} file: {file_path}")
                is_wlm = file.endswith('.wlm') or file.endswith('.wlm.not')
                try:
                    analysis_result = parse_wlw_or_wlm_file(file_path, is_wlm, verbose)
                    generate_combined_stl_file(file_path, analysis_result, output_dir, relative_root, verbose)
                except Exception as e:
                    print(f"Error processing file {file_path}: {e}")
                    continue
            else:
                if verbose:
                    print(f"Skipping non-WLW/WLM file: {file_path}")

    if verbose:
        print("Analysis complete.")

def main():
    parser = argparse.ArgumentParser(description='Analyze WLW and WLM files in a directory and generate combined heightmap STL files.')
    parser.add_argument('input_directory', type=str, help='Directory containing WLW and WLM files to analyze')
    parser.add_argument('output_dir', type=str, help='Directory to save the generated analysis and STL files')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    args = parser.parse_args()

    analyze_files(args.input_directory, args.output_dir, args.verbose)

if __name__ == '__main__':
    main()
