import os
import argparse
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from skimage import measure
import stl.mesh as stl_mesh

def create_height_map(image_path, scale_factor=1, depth=10):
    # Read the image
    image = Image.open(image_path)
    # Resize the image based on the scale factor
    resized_image = image.resize((int(image.width * scale_factor), int(image.height * scale_factor)), Image.LANCZOS)
    # Convert the resized image to grayscale
    grayscale_image = resized_image.convert('L')
    # Normalize the pixel values to the range [0, 1]
    normalized_image = np.array(grayscale_image) / 255.0
    # Create the 3D volume using the normalized image data
    height_map_3d = np.zeros((normalized_image.shape[0], normalized_image.shape[1], depth))
    for z in range(depth):
        height_map_3d[:, :, z] = normalized_image * (z / depth)
    return height_map_3d

def build_3d_model(height_map_3d, output_file, export_format):
    mesh_data = measure.marching_cubes(height_map_3d)
    mesh_vertices = mesh_data[0]
    mesh_faces = mesh_data[1]

    if export_format == 'obj':
        with open(output_file + '.obj', 'w') as f:
            for v in mesh_vertices:
                f.write(f"v {v[0]} {v[1]} {v[2]}\n")
            for face in mesh_faces:
                f.write(f"f {' '.join(map(str, face + 1))}\n")
        print(f"3D model exported as {output_file}.obj (OBJ format)")
    elif export_format == 'stl':
        mesh = stl_mesh.Mesh(np.zeros(0), np.zeros(0))
        mesh.save(output_file + '.stl', mode=stl_mesh.Mode.ASCII, update_normals=False, name='mesh')
        print(f"3D model exported as {output_file}.stl (STL format)")
    else:
        print("Unsupported export format. Please choose either 'obj' or 'stl'.")

def main():
    parser = argparse.ArgumentParser(description="Generate height maps at multiple scale factors from a single image and build a 3D model")
    parser.add_argument("image_path", help="Path to the input image file")
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

    combined_mesh_vertices = []
    combined_mesh_faces = []

    current_scale = args.min_scale
    while current_scale <= args.max_scale:
        height_map_3d = create_height_map(args.image_path, scale_factor=current_scale, depth=args.depth)

        texture_file = os.path.join(args.output_dir, f"texture_scale_{current_scale}.png")
        height_map_image = Image.fromarray((height_map_3d[:, :, 0] * 255).astype(np.uint8))
        height_map_image.save(texture_file)

        mesh_data = measure.marching_cubes(height_map_3d)
        mesh_vertices = mesh_data[0]
        mesh_faces = mesh_data[1]

        combined_mesh_vertices.extend(mesh_vertices)
        combined_mesh_faces.extend(mesh_faces + len(combined_mesh_vertices))

        build_3d_model(height_map_3d, os.path.join(args.output_dir, args.output_file + f"_scale_{current_scale}"), args.export_format)

        current_scale += args.step_size

        plt.close()

    if args.export_format == 'obj':
        with open(os.path.join(args.output_dir, args.output_file + f"_combined.obj"), 'w') as f:
            for v in combined_mesh_vertices:
                f.write(f"v {v[0]} {v[1]} {v[2]}\n")
            for face in combined_mesh_faces:
                f.write(f"f {' '.join(map(str, face + 1))}\n")
        print(f"Combined 3D model exported as {args.output_file}_combined.obj (OBJ format)")
    elif args.export_format == 'stl':
        combined_mesh = stl_mesh.Mesh(np.zeros(0), np.zeros(0))
        combined_mesh.save(os.path.join(args.output_dir, args.output_file + f"_combined.stl"), mode=stl_mesh.Mode.ASCII, update_normals=False, name='mesh')
        print(f"Combined 3D model exported as {args.output_file}_combined.stl (STL format)")

if __name__ == "__main__":
    main()
