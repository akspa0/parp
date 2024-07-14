import argparse
import os
import struct
import trimesh
import json
from copy import deepcopy

# Mapping liquid types to human-readable strings and textures
LIQUID_TYPE_MAPPING = {
    0: 'still',
    1: 'ocean',
    2: '?',
    3: 'slime',
    4: 'river',
    6: 'magma',
    8: 'fast flowing'
}

TEXTURE_MAPPING = {
    'ocean': 'Blue_1.png',
    'still': 'WaterBlue_1.png',
    'river': 'WaterBlue_1.png',
    'fast flowing': 'WaterBlue_1.png',
    'magma': 'Red_1.png',
    '?': 'Grey_1.png',
    'slime': 'Green_1.png'
}

COORDINATE_THRESHOLD = 32767

def parse_wlw_or_wlm_file(file_path, is_wlm=False, verbose=False):
    if verbose:
        print(f"Parsing {'WLM' if is_wlm else 'WLW'} file: {file_path}")

    try:
        with open(file_path, 'rb') as file:
            data = file.read()
            if len(data) < 16:
                if verbose:
                    print(f"File is too short to contain required header: {file_path}")
                return None

            magic, version, unk06, liquid_type, padding, block_count = struct.unpack('4sHHHHI', data[:16])
            magic = magic.decode('utf-8')
            
            result = {
                'magic': magic,
                'version': version,
                'unk06': unk06,
                'liquid_type': liquid_type if not is_wlm else 6,  # WLM files always have liquidType as 6 (Magma)
                'liquid_type_str': LIQUID_TYPE_MAPPING.get(liquid_type if not is_wlm else 6, 'unknown'),
                'padding': padding,
                'block_count': block_count,
                'blocks': []
            }

            offset = 16
            for _ in range(block_count):
                if offset + 48 * 4 + 2 * 4 + 80 * 2 > len(data):
                    if verbose:
                        print(f"File is too short to contain expected block data: {file_path}")
                    return None
                vertices = [struct.unpack('3f', data[offset + i * 12: offset + (i + 1) * 12]) for i in range(16)]
                offset += 48 * 4
                coord = struct.unpack('2f', data[offset:offset + 2 * 4])
                offset += 2 * 4
                block_data = struct.unpack('80H', data[offset:offset + 80 * 2])
                offset += 80 * 2
                result['blocks'].append({'vertices': vertices, 'coord': coord, 'data': block_data})

        if verbose:
            print(f"Finished parsing {'WLM' if is_wlm else 'WLW'} file: {file_path}")
        
        return result

    except Exception as e:
        print(f"Error processing {'WLM' if is_wlm else 'WLW'} file {file_path}: {e}")
        return None

def parse_wlq_file(file_path, verbose=False):
    if verbose:
        print(f"Parsing WLQ file: {file_path}")

    try:
        with open(file_path, 'rb') as file:
            data = file.read()
            if len(data) < 16:
                if verbose:
                    print(f"File is too short to contain required header: {file_path}")
                return None

            magic, version, unk06, liquid_type, padding, block_count = struct.unpack('4sHHHHI', data[:16])
            magic = magic.decode('utf-8')
            
            result = {
                'magic': magic,
                'version': version,
                'unk06': unk06,
                'liquid_type': liquid_type,
                'liquid_type_str': LIQUID_TYPE_MAPPING.get(liquid_type, 'unknown'),
                'padding': padding,
                'block_count': block_count,
                'blocks': []
            }

            offset = 16
            for _ in range(block_count):
                if offset + 48 * 4 + 2 * 4 + 80 * 2 > len(data):
                    if verbose:
                        print(f"File is too short to contain expected block data: {file_path}")
                    return None
                vertices = [struct.unpack('3f', data[offset + i * 12: offset + (i + 1) * 12]) for i in range(16)]
                offset += 48 * 4
                coord = struct.unpack('2f', data[offset:offset + 2 * 4])
                if coord[0] > COORDINATE_THRESHOLD or coord[1] > COORDINATE_THRESHOLD:
                    if verbose:
                        print(f"Invalid coordinate value in WLQ file {file_path}: {coord}")
                    continue
                offset += 2 * 4
                block_data = struct.unpack('80H', data[offset:offset + 80 * 2])
                offset += 80 * 2
                result['blocks'].append({'vertices': vertices, 'coord': coord, 'data': block_data})

        if verbose:
            print(f"Finished parsing WLQ file: {file_path}")
        
        return result

    except Exception as e:
        print(f"Error processing WLQ file {file_path}: {e}")
        return None

def ensure_manifold(mesh):
    """
    Ensures the mesh is manifold by repairing it using trimesh's built-in repair functions.
    """
    mesh.process()
    return mesh

def generate_mtl_file(obj_filename, texture_filename):
    """
    Generates an MTL file for the given OBJ file with the specified texture.
    """
    mtl_filename = obj_filename.replace('.obj', '.mtl')
    mtl_content = f"""newmtl material_0
Ka 1.000 1.000 1.000
Kd 1.000 1.000 1.000
Ks 0.000 0.000 0.000
d 1.0
illum 2
map_Kd {texture_filename}
"""
    with open(mtl_filename, 'w') as f:
        f.write(mtl_content)
    return os.path.basename(mtl_filename)

def generate_trimesh_obj_files(file_path, analysis_result, wlq_result, output_dir, relative_path, combined_vertices, combined_faces, combined_materials, verbose=False):
    """
    Generates OBJ files using trimesh representing the heightmap from WLW/WLM file data.
    Generates an additional filled 3D object with added thickness.
    Ensures the models are manifold.
    Adds the data to combined vertices and faces for a single combined mesh.
    """
    if not analysis_result:
        return

    if verbose:
        print(f"Generating OBJ files for: {file_path}")

    obj_output_dir = os.path.join(output_dir, relative_path)
    os.makedirs(obj_output_dir, exist_ok=True)
    
    vertices = []
    faces = []

    for block in analysis_result['blocks']:
        base_index = len(vertices)
        vertices.extend(block['vertices'])

        for i in range(3):
            for j in range(3):
                v1 = base_index + i * 4 + j
                v2 = base_index + i * 4 + (j + 1)
                v3 = base_index + (i + 1) * 4 + (j + 1)
                v4 = base_index + (i + 1) * 4 + j
                faces.append([v1, v2, v3])
                faces.append([v1, v3, v4])

    if wlq_result:
        for block in wlq_result['blocks']:
            base_index = len(vertices)
            vertices.extend(block['vertices'])

            for i in range(3):
                for j in range(3):
                    v1 = base_index + i * 4 + j
                    v2 = base_index + i * 4 + (j + 1)
                    v3 = base_index + (i + 1) * 4 + (j + 1)
                    v4 = base_index + (i + 1) * 4 + j
                    faces.append([v1, v2, v3])
                    faces.append([v1, v3, v4])

    original_mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
    original_mesh = ensure_manifold(original_mesh)

    liquid_type_str = analysis_result['liquid_type_str']
    texture_filename = TEXTURE_MAPPING.get(liquid_type_str, 'Grey_1.png')

    file_extension = '.wlw.obj' if file_path.endswith('.wlw') else '.wlm.obj'
    obj_filename = os.path.join(obj_output_dir, os.path.splitext(os.path.basename(file_path))[0] + file_extension)
    original_mesh.export(obj_filename)
    
    mtl_filename = generate_mtl_file(obj_filename, texture_filename)
    
    with open(obj_filename, 'r') as file:
        obj_data = file.read()
    
    with open(obj_filename, 'w') as file:
        file.write(f"mtllib {mtl_filename}\n" + obj_data)

    if verbose:
        print(f"Original OBJ file generated: {obj_filename}")

    thickness = 10.0
    top_vertices = deepcopy(vertices)
    bottom_vertices = [[v[0], v[1], v[2] - thickness] for v in vertices]
    filled_vertices = top_vertices + bottom_vertices

    side_faces = []
    num_vertices = len(vertices)
    for i in range(num_vertices):
        next_i = (i + 1) % num_vertices
        side_faces.append([i, next_i, next_i + num_vertices])
        side_faces.append([i, next_i + num_vertices, i + num_vertices])

    bottom_faces = [[f[0] + num_vertices, f[2] + num_vertices, f[1] + num_vertices] for f in faces]

    filled_faces = faces + bottom_faces + side_faces

    filled_mesh = trimesh.Trimesh(vertices=filled_vertices, faces=filled_faces)
    filled_mesh = ensure_manifold(filled_mesh)

    filled_obj_filename = os.path.join(obj_output_dir, '3d_' + os.path.splitext(os.path.basename(file_path))[0] + file_extension)
    filled_mesh.export(filled_obj_filename)

    filled_mtl_filename = generate_mtl_file(filled_obj_filename, texture_filename)

    with open(filled_obj_filename, 'r') as file:
        filled_obj_data = file.read()
    
    with open(filled_obj_filename, 'w') as file:
        file.write(f"mtllib {filled_mtl_filename}\n" + filled_obj_data)

    if verbose:
        print(f"Filled 3D OBJ file generated: {filled_obj_filename}")

    # Add to combined vertices and faces
    combined_base_index = len(combined_vertices)
    combined_vertices.extend(vertices)
    combined_faces.extend([[v[0] + combined_base_index, v[1] + combined_base_index, v[2] + combined_base_index] for v in faces])
    
    combined_materials.append({
        'material_name': f"material_{liquid_type_str}",
        'texture_file': texture_filename
    })

def generate_combined_mesh(combined_vertices, combined_faces, combined_materials, output_dir, folder_name, verbose=False):
    """
    Generates a single combined mesh from all input files.
    Links them together via a base plane at z=-25.
    """
    base_plane_z = -25.0
    base_plane_vertices = [
        [v[0], v[1], base_plane_z] for v in combined_vertices
    ]

    combined_mesh = trimesh.Trimesh(vertices=combined_vertices + base_plane_vertices, faces=combined_faces)
    combined_mesh = ensure_manifold(combined_mesh)

    combined_filename = os.path.join(output_dir, f'combined_{folder_name}.obj')
    combined_mesh.export(combined_filename)

    if verbose:
        print(f"Combined mesh OBJ file generated: {combined_filename}")

def export_combined_mesh_as_gltf(combined_vertices, combined_faces, combined_materials, output_dir, folder_name, verbose=False):
    """
    Exports the combined mesh as a GLTF file with textures applied.
    """
    from trimesh.exchange.gltf import export_gltf

    base_plane_z = -25.0
    base_plane_vertices = [
        [v[0], v[1], base_plane_z] for v in combined_vertices
    ]

    combined_mesh = trimesh.Trimesh(vertices=combined_vertices + base_plane_vertices, faces=combined_faces)

    materials = []
    for material in combined_materials:
        materials.append(trimesh.visual.material.PBRMaterial(
            name=material['material_name'],
            baseColorTexture=trimesh.visual.TextureVisuals(
                uv=[(0, 0), (1, 0), (1, 1), (0, 1)],
                image=material['texture_file']
            )
        ))

    combined_mesh.visual = trimesh.visual.TextureVisuals(materials=materials)
    gltf_data = export_gltf(combined_mesh)

    gltf_filename = os.path.join(output_dir, f'combined_{folder_name}.gltf')
    with open(gltf_filename, 'wb') as f:
        f.write(gltf_data)

    if verbose:
        print(f"Combined mesh GLTF file generated: {gltf_filename}")

def analyze_files(input_directory, output_dir, export_format, verbose=False):
    if verbose:
        print(f"Starting analysis of WLW, WLM, and WLQ files in directory: {input_directory}")
        
    for root, _, files in os.walk(input_directory):
        relative_root = os.path.relpath(root, input_directory)
        if verbose:
            print(f"Checking directory: {root} (relative: {relative_root})")
        
        combined_vertices = []
        combined_faces = []
        combined_materials = []
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
                    wlq_result = None
                    wlq_file_path = file_path.replace('.wlw', '.wlq').replace('.wlm', '.wlq')
                    if os.path.exists(wlq_file_path):
                        wlq_result = parse_wlq_file(wlq_file_path, verbose)
                    folder_results.append((file_path, analysis_result, wlq_result, relative_root))
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
        output_json_file = os.path.join(output_dir, f"{os.path.basename(root)}.json")

        os.makedirs(output_dir, exist_ok=True)

        if verbose:
            print(f"Writing analysis results to: {output_analysis_file}")

        results_json = []

        with open(output_analysis_file, 'w') as f:
            for file_path, analysis_result, wlq_result, relative_root in folder_results:
                if analysis_result is None:
                    continue
                f.write(f"\nAnalyzing file: {file_path}\n")
                f.write(f"Liquid type: {analysis_result['liquid_type_str']} ({analysis_result['liquid_type']})\n")
                for key, value in analysis_result.items():
                    if key != 'blocks':
                        f.write(f"{key}: {value}\n")
                if wlq_result:
                    f.write("\nWLQ File Info:\n")
                    for key, value in wlq_result.items():
                        f.write(f"{key}: {value}\n")

                result_data = {
                    "file_path": file_path,
                    "analysis_result": analysis_result,
                    "wlq_result": wlq_result
                }
                results_json.append(result_data)
                generate_trimesh_obj_files(file_path, analysis_result, wlq_result, output_dir, relative_root, combined_vertices, combined_faces, combined_materials, verbose)

        with open(output_json_file, 'w') as f:
            json.dump(results_json, f, indent=4)

        # Generate combined mesh for the current folder
        generate_combined_mesh(combined_vertices, combined_faces, combined_materials, output_dir, os.path.basename(root), verbose)

        # Optionally export as glTF
        if export_format == 'gltf':
            export_combined_mesh_as_gltf(combined_vertices, combined_faces, combined_materials, output_dir, os.path.basename(root), verbose)

    if verbose:
        print("Analysis complete.")

def main():
    parser = argparse.ArgumentParser(description='Analyze WLW, WLM, and WLQ files in a directory and generate heightmap OBJ files.')
    parser.add_argument('input_directory', type=str, help='Directory containing WLW, WLM, and WLQ files to analyze')
    parser.add_argument('output_dir', type=str, help='Directory to save the generated analysis and OBJ files')
    parser.add_argument('--export-format', type=str, choices=['obj', 'gltf'], default='obj', help='Export format for the combined mesh')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    args = parser.parse_args()

    analyze_files(args.input_directory, args.output_dir, args.export_format, args.verbose)

if __name__ == '__main__':
    main()
