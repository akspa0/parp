import os
import sys
import argparse
import cv2
import numpy as np
import open3d as o3d
from tqdm import tqdm

def preprocess_image(image, z_scale=0.0625, allow_negative_z=True, flip_x=False, flip_y=False):
    # Convert image to point cloud
    depth = np.where(image > 0, image, 0).astype(np.float32)
    points = []
    for y in range(depth.shape[0]):
        for x in range(depth.shape[1]):
            if flip_x:
                x = depth.shape[1] - x - 1
            if flip_y:
                y = depth.shape[0] - y - 1
            z = -depth[y, x] * z_scale  # Make Z-axis negative
            if not allow_negative_z:
                z = max(z, 0)  # Ensure non-negative Z-axis values
            points.append([x, -y, z])  # Make Y-axis negative
    return points

def generate_mesh(points, debug=False):
    # Convert points to Open3D PointCloud
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    
    # Estimate normals
    if debug:
        print("Estimating normals...")
    with open(os.devnull, 'w') as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30))
        sys.stdout = old_stdout
    
    # Generate mesh using Poisson surface reconstruction
    if debug:
        print("Generating mesh...")
    with open(os.devnull, 'w') as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd)
        sys.stdout = old_stdout
    
    # Ensure the mesh is polygon-filled
    mesh.compute_triangle_normals()
    mesh.compute_vertex_normals()
    mesh.remove_duplicated_vertices()
    mesh.remove_unreferenced_vertices()
    mesh.remove_degenerate_triangles()
    mesh.remove_unreferenced_vertices()

    # Smooth the mesh
    if debug:
        print("Smoothing mesh...")
    with open(os.devnull, 'w') as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        mesh.filter_smooth_taubin(10, 0.5, -0.53)
        sys.stdout = old_stdout
    
    return mesh

def main(input_dir, output_dir, downsample=False, z_scale=0.0625, merge=False, debug=False, allow_negative_z=True, flip_x=False, flip_y=False, batch_size=1):
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get list of input images
    input_images = [filename for filename in os.listdir(input_dir) if filename.endswith(".png")]
    
    # Batch processing
    num_batches = int(np.ceil(len(input_images) / batch_size))
    for batch_idx in tqdm(range(num_batches), desc="Processing", dynamic_ncols=True):
        batch_start_idx = batch_idx * batch_size
        batch_end_idx = min((batch_idx + 1) * batch_size, len(input_images))
        batch_input_images = input_images[batch_start_idx:batch_end_idx]
        
        for filename in batch_input_images:
            input_path = os.path.join(input_dir, filename)
            output_filename = f"mesh_{filename[:-4]}.obj"
            output_path = os.path.join(output_dir, output_filename)
            
            try:
                image = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)
                if downsample:
                    image = cv2.resize(image, None, fx=0.5, fy=0.5)
                points = preprocess_image(image, z_scale, allow_negative_z, flip_x, flip_y)
                mesh = generate_mesh(points, debug)
                o3d.io.write_triangle_mesh(output_path, mesh)
            except Exception as e:
                print(f"Error processing {filename}: {e}")
    
    # Merge meshes if specified
    if merge:
        merged_mesh = o3d.geometry.TriangleMesh()
        for filename in os.listdir(output_dir):
            if filename.endswith(".obj"):
                mesh = o3d.io.read_triangle_mesh(os.path.join(output_dir, filename))
                merged_mesh += mesh
        o3d.io.write_triangle_mesh(os.path.join(output_dir, "merged_mesh.obj"), merged_mesh)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate 3D meshes from overhead mini map images")
    parser.add_argument("input_dir", type=str, help="Directory containing input overhead mini map images")
    parser.add_argument("output_dir", type=str, help="Directory to save output OBJ 3D meshes")
    parser.add_argument("--downsample", action="store_true", help="Optional flag to downsample input images")
    parser.add_argument("--z_scale", type=float, default=0.0625, help="Optional parameter to scale the Z-axis of the generated meshes")
    parser.add_argument("--merge", action="store_true", help="Optional flag to merge all generated meshes into a single mesh")
    parser.add_argument("--debug", action="store_true", help="Optional flag to enable debug mode with verbose output")
    parser.add_argument("--allow_negative_z", action="store_true", help="Optional flag to allow negative Z-axis values in the generated meshes")
    parser.add_argument("--flip_x", action="store_true", help="Optional flag to flip X-axis coordinates")
    parser.add_argument("--flip_y", action="store_true", help="Optional flag to flip Y-axis coordinates")
    parser.add_argument("--batch_size", type=int, default=1, help="Batch size for processing multiple tiles simultaneously")
    args = parser.parse_args()
    
    main(args.input_dir, args.output_dir, args.downsample, args.z_scale, args.merge, args.debug, args.allow_negative_z, args.flip_x, args.flip_y, args.batch_size)
