import os
import shutil
import argparse

def create_material_mtl(mesh_file, texture_file, output_folder):
    # Extract mesh filename without extension
    mesh_name = os.path.splitext(os.path.basename(mesh_file))[0]

    # Creating material file content
    material_content = f"""
newmtl {mesh_name}
Ka 1.000 1.000 1.000
Kd 1.000 1.000 1.000
Ks 0.000 0.000 0.000
Tr 1.000
illum 1
Ns 0.000
map_Kd {texture_file}
"""

    # Writing material content to the material file
    material_file = os.path.join(output_folder, f"{mesh_name}.mtl")
    with open(material_file, 'w') as f:
        f.write(material_content)

    return material_file

def flip_z_axis(mesh_file, output_folder):
    # Read the mesh file and flip the z-axis
    with open(mesh_file, 'r') as f:
        lines = f.readlines()
    # Flip the z-coordinate of each vertex
    flipped_lines = [line.replace('v ', 'v -') if line.startswith('v ') else line for line in lines]
    # Write the modified mesh file
    flipped_mesh_file = os.path.join(output_folder, os.path.basename(mesh_file))
    with open(flipped_mesh_file, 'w') as f:
        f.writelines(flipped_lines)
    return flipped_mesh_file

def export_meshes_and_textures(mesh_folder, texture_folder, output_folder):
    # Create the output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Copy mesh files to the output folder and flip the z-axis
    for mesh_file in os.listdir(mesh_folder):
        if mesh_file.startswith('mesh_tile_') and mesh_file.endswith('.obj'):
            mesh_path = os.path.join(mesh_folder, mesh_file)
            flipped_mesh_file = flip_z_axis(mesh_path, output_folder)
            # Find corresponding texture file
            texture_name = f"tile{mesh_file[9:-4]}.png"
            texture_path = os.path.join(texture_folder, texture_name)
            if os.path.exists(texture_path):
                # Copy texture file to the output folder
                shutil.copy(texture_path, output_folder)
                # Create material file for the mesh
                create_material_mtl(flipped_mesh_file, texture_name, output_folder)

def main(args):
    export_meshes_and_textures(args.mesh_folder, args.texture_folder, args.output_folder)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Export 3D meshes and textures.')
    parser.add_argument('mesh_folder', help='Path to the folder containing 3D mesh files.')
    parser.add_argument('texture_folder', help='Path to the folder containing texture files.')
    parser.add_argument('output_folder', help='Path to the output folder.')
    args = parser.parse_args()
    
    main(args)
