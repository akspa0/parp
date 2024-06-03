import argparse
import os
import struct

def parse_wlw_file(file_path, verbose=False):
    """
    Parses a WLW file and extracts informative data.
    """
    if verbose:
        print(f"Parsing file: {file_path}")
        
    with open(file_path, 'rb') as file:
        data = file.read()
        
        # Read header
        magic, version, unk06, liquid_type, padding, block_count = struct.unpack('4sHHHHI', data[:16])
        magic = magic.decode('utf-8')

        result = {
            'magic': magic,
            'version': version,
            'unk06': unk06,
            'liquid_type': liquid_type,
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

def generate_obj_file(file_path, analysis_result, output_dir, verbose=False):
    """
    Generates a simple OBJ file representing the heightmap from WLW file data.
    """
    if verbose:
        print(f"Generating OBJ file for: {file_path}")
    
    vertices = []
    faces = []

    for block_index, block in enumerate(analysis_result['blocks']):
        base_index = len(vertices) + 1
        vertices.extend(block['vertices'])

        # Create faces using the grid structure
        for i in range(3):
            for j in range(3):
                v1 = base_index + i * 4 + j
                v2 = base_index + i * 4 + (j + 1)
                v3 = base_index + (i + 1) * 4 + (j + 1)
                v4 = base_index + (i + 1) * 4 + j
                faces.append((v1, v2, v3))
                faces.append((v1, v3, v4))

    obj_filename = os.path.join(output_dir, os.path.basename(file_path).replace('.wlw', '.obj'))
    with open(obj_filename, 'w') as f:
        for v in vertices:
            f.write(f"v {v[0]} {v[1]} {v[2]}\n")
        for face in faces:
            f.write(f"f {face[0]} {face[1]} {face[2]}\n")

    if verbose:
        print(f"OBJ file generated: {obj_filename}")

def analyze_files(input_directory, output_file, output_dir, verbose=False):
    """
    Analyzes WLW files in the input directory and prints informative data.
    Generates OBJ files for visualizing the heightmaps.
    """
    if verbose:
        print(f"Starting analysis of WLW files in directory: {input_directory}")
        
    results = []
    for root, _, files in os.walk(input_directory):
        if verbose:
            print(f"Checking directory: {root}")
        for file in files:
            file_path = os.path.join(root, file)
            if verbose:
                print(f"Found file: {file_path}")
            if file.endswith('.wlw'):
                if verbose:
                    print(f"Processing WLW file: {file_path}")
                analysis_result = parse_wlw_file(file_path, verbose)
                results.append((file_path, analysis_result))
            else:
                if verbose:
                    print(f"Skipping non-WLW file: {file_path}")

    if not results:
        if verbose:
            print("No WLW files found in the specified directory.")
        return

    # Ensure the output directories exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    if verbose:
        print(f"Writing analysis results to: {output_file}")

    with open(output_file, 'w') as f:
        for file_path, analysis_result in results:
            f.write(f"\nAnalyzing file: {file_path}\n")
            for key, value in analysis_result.items():
                f.write(f"{key}: {value}\n")
            generate_obj_file(file_path, analysis_result, output_dir, verbose)

    if verbose:
        print("Analysis complete.")

def main():
    parser = argparse.ArgumentParser(description='Analyze WLW files in a directory and generate heightmap OBJ files.')
    parser.add_argument('input_directory', type=str, help='Directory containing WLW files to analyze')
    parser.add_argument('output_file', type=str, help='File to output the analysis results')
    parser.add_argument('output_dir', type=str, help='Directory to save the generated OBJ files')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    args = parser.parse_args()

    analyze_files(args.input_directory, args.output_file, args.output_dir, args.verbose)

if __name__ == '__main__':
    main()
