import os
import argparse
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from skimage import measure
import stl.mesh as stl_mesh
from tqdm import tqdm

def create_height_map(image, scale_factor=1, depth=10):
    resized_image = image.resize((int(image.width * scale_factor), int(image.height * scale_factor)), Image.LANCZOS)
    normalized_image = np.array(resized_image) / 255.0
    height_map_3d = np.zeros((normalized_image.shape[0], normalized_image.shape[1], depth))
    for z in range(depth):
        height_map_3d[:, :, z] = normalized_image[:, :, 0] * (z / depth)
    return height_map_3d

def build_3d_model(vertices, faces, output_file, export_format, texture_file=None):
    try:
        if export_format == 'obj':
            with open(output_file + '.obj', 'w') as f:
                for v in vertices:
                    f.write(f"v {v[0]} {v[1]} {v[2]}\n")
                if texture_file:
                    f.write(f"mtllib {output_file}.mtl\n")
                    f.write(f"usemtl {os.path.splitext(os.path.basename(texture_file))[0]}\n")
                for face in faces:
                    f.write("f ")
                    f.write(" ".join(str(i + 1) for i in face))
                    f.write("\n")
            print(f"3D model exported as {output_file}.obj (OBJ format)")
        elif export_format == 'stl':
            mesh = stl_mesh.Mesh(np.zeros(0), np.zeros(0))
            mesh.save(output_file + '.stl', mode=stl_mesh.Mode.ASCII, update_normals=False, name='mesh')
            print(f"3D model exported as {output_file}.stl (STL format)")
        else:
            print("Unsupported export format. Please choose either 'obj' or 'stl'.")
    except Exception as e:
        print(f"Error occurred while exporting 3D model: {e}")

def merge_models(input_dir, output_file, export_format):
    # Create output directory if it doesn't exist
    os.makedirs(output_file, exist_ok=True)
    
    merged_vertices = []
    merged_faces = []

    # Collect all vertices and faces from individual tiles
    for file in os.listdir(input_dir):
        if file.endswith(".obj"):
            with open(os.path.join(input_dir, file), 'r') as f:
                vertices = []
                faces = []
                for line in f:
                    if line.startswith("v "):
                        vertices.append([float(x) for x in line.strip().split()[1:]])
                    elif line.startswith("f "):
                        faces.append([int(x.split('/')[0]) - 1 for x in line.strip().split()[1:]])

                # Offset vertices index
                offset = len(merged_vertices)
                for face in faces:
                    merged_faces.append([v + offset for v in face])
                
                merged_vertices.extend(vertices)

    # Calculate the number of tiles in each dimension
    num_tiles = int(np.ceil(np.sqrt(len(os.listdir(input_dir)))))

    # Calculate tile size
    tile_size = len(merged_vertices) // num_tiles

    # Rearrange vertices to align on a grid
    for i in range(num_tiles):
        for j in range(num_tiles):
            tile_vertices = merged_vertices[i * num_tiles * tile_size + j * tile_size: 
                                            i * num_tiles * tile_size + (j + 1) * tile_size]
            tile_faces = merged_faces[i * num_tiles * tile_size + j * tile_size: 
                                      i * num_tiles * tile_size + (j + 1) * tile_size]

            output_tile_file = os.path.join(output_file, f"tile_{i}_{j}")
            build_3d_model(tile_vertices, tile_faces, output_tile_file, export_format)

def main():
    parser = argparse.ArgumentParser(description="Generate height maps at multiple scale factors from a single image and build a 3D model")
    parser.add_argument("image_path", help="Path to the directory containing input image files")
    parser.add_argument("--min-scale", type=float, default=1, help="Minimum scale factor (default: 1)")
    parser.add_argument("--max-scale", type=float, required=True, help="Maximum scale factor")
    parser.add_argument("--step-size", type=float, default=1, help="Step size between scale factors (default: 1)")
    parser.add_argument("--depth", type=int, default=10, help="Depth of the 3D volume (default: 10)")
    parser.add_argument("--output-dir", "-o", default="height_maps", help="Output directory for height maps (default: height_maps)")
    parser.add_argument("--export-format", "-f", default="stl", choices=["obj", "stl"], help="Export format for the 3D model (default: stl)")
    parser.add_argument("--output-file", "-out", default="model", help="Output filename for the 3D model (default: model)")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    plt.ioff()  # Turn interactive plotting off

    image_files = [f for f in os.listdir(args.image_path) if f.endswith('.png') or f.endswith('.jpg')]
    for image_file in tqdm(image_files, desc='Processing Tiles'):
        image_path = os.path.join(args.image_path, image_file)
        image = Image.open(image_path)
        current_scale = args.min_scale
        while current_scale <= args.max_scale:
            height_map_3d = create_height_map(image, scale_factor=current_scale, depth=args.depth)

            texture_file = os.path.join(args.output_dir, f"texture_{os.path.splitext(image_file)[0]}_scale_{current_scale}.png")
            height_map_image = Image.fromarray((height_map_3d[:, :, 0] * 255).astype(np.uint8))
            height_map_image.save(texture_file)

            mesh_data = measure.marching_cubes(height_map_3d)
            mesh_vertices = mesh_data[0]
            mesh_faces = mesh_data[1]

            output_file = os.path.join(args.output_dir, f"{os.path.splitext(image_file)[0]}_scale_{current_scale}")
            build_3d_model(mesh_vertices, mesh_faces, output_file, args.export_format, texture_file)

            current_scale += args.step_size

            plt.close()

    # Merge models
    merge_models(args.output_dir, os.path.join(args.output_dir, args.output_file), args.export_format)

if __name__ == "__main__":
    main()
