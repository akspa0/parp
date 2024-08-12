import argparse
import os
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from PIL import Image
from skimage import measure
from stl import mesh as stl_mesh

def create_height_map(image_path, scale_factor, depth):
    # Open the image
    img = Image.open(image_path).convert('L')  # Convert to grayscale
    
    # Convert the image to a numpy array
    img_array = np.array(img)
    
    # Normalize the values to be in the range [0, 1]
    img_array_normalized = img_array / 255.0
    
    # Apply the scale factor to adjust the height
    img_array_normalized *= scale_factor
    
    # Create a 3D volume
    height_map_3d = np.repeat(img_array_normalized[:, :, np.newaxis], depth, axis=2)
    
    return height_map_3d

def build_3d_model(height_map_3d, output_file, export_format, texture_file):
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Create grid coordinates
    x_dim, y_dim, z_dim = height_map_3d.shape
    X, Y = np.meshgrid(range(y_dim), range(x_dim))
    Z = height_map_3d[:, :, 0]  # Take one slice of the 3D volume for height values

    # Read texture image and convert to RGBA format
    texture_image = plt.imread(texture_file)
    if texture_image.ndim == 2:  # Grayscale image, convert to RGB
        texture_image = plt.cm.gray(texture_image)
    elif texture_image.shape[2] == 1:  # Single-channel image, convert to RGB
        texture_image = plt.cm.gray(texture_image[:, :, 0])
    elif texture_image.shape[2] == 3:  # RGB image, convert to RGBA
        texture_image = np.dstack((texture_image, np.ones((texture_image.shape[0], texture_image.shape[1]))))
    elif texture_image.shape[2] != 4:  # Invalid format
        raise ValueError("Unsupported texture image format. Must be RGB or RGBA.")

    # Plot 3D surface with texture
    ax.plot_surface(X, Y, Z, facecolors=texture_image, rstride=1, cstride=1, linewidth=0)

    # Set labels and scaling
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')

    # Save the 3D model
    if export_format == 'obj':
        plt.savefig(output_file + '.png')  # Save a PNG image for texture mapping
        mesh = measure.marching_cubes(height_map_3d)
        mesh_vertices = mesh[0] + [0, 0, 0]
        mesh_faces = mesh[1]
        with open(output_file + '.obj', 'w') as f:
            for v in mesh_vertices:
                f.write(f"v {v[0]} {v[1]} {v[2]}\n")
            for face in mesh_faces:
                f.write(f"f {' '.join(map(str, face + 1))}\n")
        print(f"3D model exported as {output_file}.obj (OBJ format)")
    elif export_format == 'stl':
        mesh = measure.marching_cubes(height_map_3d)
        mesh_vertices = mesh[0] + [0, 0, 0]
        mesh_faces = mesh[1]
        stl_mesh.Mesh(np.zeros(0), np.zeros(0)).save(output_file + '.stl', mode=stl_mesh.Mode.ASCII, update_normals=False, name='mesh')
        with open(output_file + '.stl', 'wb') as f:
            mesh = stl_mesh.Mesh(np.zeros(0), np.zeros(0), mode=stl_mesh.Mode.ASCII, update_normals=False, name='mesh')
            mesh = stl_mesh.Mesh(np.zeros(0), np.zeros(0), mode=stl_mesh.Mode.ASCII, update_normals=False, name='mesh')
            mesh = stl_mesh.Mesh(np.zeros(0), np.zeros(0), mode=stl_mesh.Mode.ASCII, update_normals=False, name='mesh')
            mesh.save(output_file + '.stl', mode=stl_mesh.Mode.ASCII, update_normals=False, name='mesh')
        print(f"3D model exported as {output_file}.stl (STL format)")
    else:
        print("Unsupported export format. Please choose either 'obj' or 'stl'.")

    plt.show()

def main():
    # Parse command-line arguments
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

    # Create the output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)

    # Generate height maps at multiple scale factors
    current_scale = args.min_scale
    while current_scale <= args.max_scale:
        # Generate the height map
        height_map_3d = create_height_map(args.image_path, scale_factor=current_scale, depth=args.depth)

        # Save the height map as an image
        output_file = os.path.join(args.output_dir, f"height_map_scale_{current_scale}.png")
        height_map_image = Image.fromarray((height_map_3d[:, :, 0] * 255).astype(np.uint8))  # Save the first slice of the 3D volume as the image
        height_map_image.save(output_file)
        print(f"Height map at scale factor {current_scale} saved as {output_file}")

        # Generate texture file name
        texture_file = os.path.join(args.output_dir, f"texture_scale_{current_scale}.png")
        height_map_image.save(texture_file)
        print(f"Texture file for scale factor {current_scale} saved as {texture_file}")

        # Build the 3D model
        print(f"Building 3D model for height map at scale factor {current_scale}...")
        build_3d_model(height_map_3d, os.path.join(args.output_dir, args.output_file + f"_scale_{current_scale}"), args.export_format, texture_file)

        # Update the scale for the next iteration
        current_scale += args.step_size

if __name__ == "__main__":
    main()
