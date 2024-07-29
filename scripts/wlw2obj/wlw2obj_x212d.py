import argparse
import os
import struct
import numpy as np
import shutil

# Mapping liquid types to human-readable strings and corresponding texture files
LIQUID_TYPE_MAPPING = {
    0: ('still', 'Blue_1.png'),
    1: ('ocean', 'Blue_1.png'),
    2: ('?', 'Yellow_1.png'),
    3: ('slime', 'Green_1.png'),
    4: ('river', 'WaterBlue_1.png'),
    6: ('magma', 'Red_1.png'),
    8: ('fast flowing', 'Charcoal_1.png')
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
            'liquid_type_str': LIQUID_TYPE_MAPPING.get(liquid_type, ('unknown', 'Yellow_1.png'))[0],
            'texture': LIQUID_TYPE_MAPPING.get(liquid_type, ('unknown', 'Yellow_1.png'))[1],
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

def calculate_normals(vertices, faces):
    """
    Calculate normals for each face in the mesh.
    """
    normals = []
    for face in faces:
        v1, v2, v3 = np.array(vertices[face[0]]), np.array(vertices[face[1]]), np.array(vertices[face[2]])
        normal = np.cross(v2 - v1, v3 - v1)
        normal = normal / np.linalg.norm(normal)
        normals.append(normal.tolist())
    return normals

def generate_uv_coordinates(vertices):
    """
    Generate simple planar UV coordinates for the vertices.
    """
    uvs = []
    for vertex in vertices:
        u, v = vertex[0], vertex[1]
        uvs.append([u, v])
    return np.array(uvs)

def write_obj_with_mtl(filename, vertices, faces, uvs, mtl_filename):
    """
    Writes the given vertices, faces, and UVs to an OBJ file with an associated MTL file.
    """
    with open(filename, 'w') as f:
        f.write(f"mtllib {mtl_filename}\n")
        for vertex in vertices:
            f.write(f"v {vertex[0]} {vertex[1]} {vertex[2]}\n")
        for uv in uvs:
            f.write(f"vt {uv[0]} {uv[1]}\n")
        for face in faces:
            f.write(f"f {face[0]+1}/{face[0]+1} {face[1]+1}/{face[1]+1} {face[2]+1}/{face[2]+1}\n")

def write_mtl(filename, texture_filename):
    """
    Writes an MTL file that references the given texture file.
    """
    with open(filename, 'w') as f:
        f.write(f"newmtl material_1\n")
        f.write(f"map_Kd {texture_filename}\n")

def generate_obj_file(file_path, analysis_result, output_dir, relative_path, verbose=False):
    """
    Generates an OBJ file representing the heightmap from all blocks in a WLW/WLM file.
    """
    if verbose:
        print(f"Generating OBJ file for: {file_path}")

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
    uvs = generate_uv_coordinates(vertices)
    normals = calculate_normals(vertices, faces)
    
    obj_filename = os.path.join(obj_output_dir, os.path.splitext(os.path.basename(file_path))[0] + '.obj')
    mtl_filename = os.path.splitext(os.path.basename(obj_filename))[0] + '.mtl'
    texture_filename = analysis_result['texture']

    # Copy the texture file to the output directory
    texture_source_path = os.path.join(os.path.dirname(__file__), texture_filename)
    texture_dest_path = os.path.join(obj_output_dir, texture_filename)
    shutil.copyfile(texture_source_path, texture_dest_path)

    write_obj_with_mtl(obj_filename, vertices, faces, uvs, mtl_filename)
    write_mtl(os.path.join(obj_output_dir, mtl_filename), texture_filename)

    if verbose:
        print(f"OBJ file and MTL file generated: {obj_filename} and {mtl_filename}")

def write_analysis_report(analysis_reports, file_path, analysis_result):
    """
    Writes the analysis report for a given file.
    """
    report = []
    report.append(f"File: {file_path}\n")
    report.append(f"Magic: {analysis_result['magic']}\n")
    report.append(f"Version: {analysis_result['version']}\n")
    report.append(f"Unknown 06: {analysis_result['unk06']}\n")
    report.append(f"Liquid Type: {analysis_result['liquid_type_str']} ({analysis_result['liquid_type']})\n")
    report.append(f"Padding: {analysis_result['padding']}\n")
    report.append(f"Block Count: {analysis_result['block_count']}\n")
    report.append(f"Block 2 Count: {analysis_result.get('block2_count', 'N/A')}\n")
    report.append(f"Unknown: {analysis_result.get('unknown', 'N/A')}\n")
    report.append("\nBlock 2 Data:\n")
    for block2 in analysis_result['blocks2']:
        report.append(f"  _unk00: {block2['_unk00']}\n")
        report.append(f"  _unk0C: {block2['_unk0C']}\n")
        report.append(f"  _unk14: {block2['_unk14']}\n")
    
    analysis_reports.append("\n".join(report))

def analyze_folder(root, relative_root, files, output_dir, verbose=False):
    """
    Analyzes files in a single folder and generates combined OBJ files for visualizing the heightmaps.
    """
    combined_vertices = []
    combined_faces = []
    combined_uvs = []
    combined_materials = []
    analysis_reports = []

    folder_name = os.path.basename(root)

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
                
                generate_obj_file(file_path, analysis_result, output_dir, relative_root, verbose)
                write_analysis_report(analysis_reports, file_path, analysis_result)
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
                continue
        else:
            if verbose:
                print(f"Skipping non-WLW/WLM file: {file_path}")

    # Ensure the output directory exists for the combined analysis report
    combined_report_dir = os.path.join(output_dir, relative_root)
    os.makedirs(combined_report_dir, exist_ok=True)
    
    # Write combined analysis report
    combined_report_filename = os.path.join(combined_report_dir, f'{folder_name}_combined_analysis.txt')
    with open(combined_report_filename, 'w') as combined_report_file:
        combined_report_file.write("\n".join(analysis_reports))

    if verbose:
        print("Analysis complete.")
        print(f"Combined analysis report generated: {combined_report_filename}")

def analyze_files(input_directory, output_dir, verbose=False):
    """
    Analyzes WLW and WLM files in the input directory and generates combined OBJ files for visualizing the heightmaps.
    """
    if verbose:
        print(f"Starting analysis of WLW and WLM files in directory: {input_directory}")
    
    for root, _, files in os.walk(input_directory):
        relative_root = os.path.relpath(root, input_directory)
        if files:
            analyze_folder(root, relative_root, files, output_dir, verbose)

def main():
    parser = argparse.ArgumentParser(description='Analyze WLW and WLM files in a directory and generate combined heightmap OBJ files with textures.')
    parser.add_argument('input_directory', type=str, help='Directory containing WLW and WLM files to analyze')
    parser.add_argument('output_dir', type=str, help='Directory to save the generated analysis and OBJ files')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    args = parser.parse_args()

    analyze_files(args.input_directory, args.output_dir, args.verbose)

if __name__ == '__main__':
    main()
