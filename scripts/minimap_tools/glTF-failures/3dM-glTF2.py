import os
import argparse
import cv2
import numpy as np
import open3d as o3d
from tqdm import tqdm
from pygltflib import GLTF2, Buffer, BufferView, Accessor, Mesh, Primitive, Node, Texture, Material, Image, Sampler

def preprocess_image(image, z_scale=0.0625, allow_negative_z=True):
    # Convert image to point cloud
    depth = np.where(image > 0, image, 0).astype(np.float32)
    points = []
    for y in range(depth.shape[0]):
        for x in range(depth.shape[1]):
            z = depth[y, x] * z_scale
            if not allow_negative_z:
                z = max(z, 0)  # Ensure non-negative Z-axis values
            points.append([-x, y, -z])  # Flip X-axis
    return points

def generate_mesh(points, debug=False):
    # Convert points to Open3D PointCloud
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    
    # Estimate normals
    if debug:
        print("Estimating normals...")
    pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30))
    
    # Generate mesh using Poisson surface reconstruction
    if debug:
        print("Generating mesh...")
    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd)
    
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
    mesh.filter_smooth_taubin(10, 0.5, -0.53)
    
    return mesh

def convert_open3d_mesh_to_gltf(mesh):
    vertices = np.asarray(mesh.vertices)
    normals = np.asarray(mesh.vertex_normals)
    triangles = np.asarray(mesh.triangles)
    
    # Initialize glTF objects
    gltf = GLTF2()
    buffer = Buffer()
    buffer_view = BufferView(buffer)
    
    # Set vertices accessor
    vertices_accessor = Accessor(buffer_view, Accessor.FLOAT_VEC3, Accessor.POSITION)
    vertices_accessor.set_array(vertices.flatten())
    vertices_accessor.normalize()
    vertices_accessor.byte_offset = 0
    vertices_accessor.byte_stride = 12
    gltf.add_accessor(vertices_accessor)
    
    # Set normals accessor
    normals_accessor = Accessor(buffer_view, Accessor.FLOAT_VEC3, Accessor.NORMAL)
    normals_accessor.set_array(normals.flatten())
    normals_accessor.normalize()
    normals_accessor.byte_offset = len(vertices_accessor.array) * 4
    normals_accessor.byte_stride = 12
    gltf.add_accessor(normals_accessor)
    
    # Set indices accessor
    indices_accessor = Accessor(buffer_view, Accessor.UNSIGNED_SHORT, Accessor.INDEX)
    indices_accessor.set_array(triangles.flatten())
    indices_accessor.byte_offset = len(vertices_accessor.array) * 4 * 3
    gltf.add_accessor(indices_accessor)
    
    # Set buffer and buffer views
    buffer.add_buffer_view(buffer_view)
    gltf.add_buffer(buffer)
    
    # Create mesh object
    mesh_obj = Mesh()
    mesh_obj.add_primitive(Primitive(vertices_accessor=vertices_accessor, normals_accessor=normals_accessor, indices_accessor=indices_accessor))
    gltf.add_mesh(mesh_obj)
    
    return gltf

def merge_meshes(meshes, textures, positions):
    merged_mesh = o3d.geometry.TriangleMesh()
    for mesh, texture, position in zip(meshes, textures, positions):
        # Transform mesh
        mesh.transform(np.array([[1, 0, 0, position[0]],
                                  [0, 1, 0, position[1]],
                                  [0, 0, 1, position[2]],
                                  [0, 0, 0, 1]]))
        # Merge mesh
        merged_mesh += mesh
    return merged_mesh

def main(input_dir, output_dir, downsample=False, z_scale=0.0625, debug=False, allow_negative_z=True, batch_size=1):
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get list of input images
    input_images = [filename for filename in os.listdir(input_dir) if filename.endswith(".png")]
    
    # Batch processing
    meshes = []
    textures = []
    positions = []
    num_batches = int(np.ceil(len(input_images) / batch_size))
    for batch_idx in tqdm(range(num_batches), desc="Processing", dynamic_ncols=True):
        batch_start_idx = batch_idx * batch_size
        batch_end_idx = min((batch_idx + 1) * batch_size, len(input_images))
        batch_input_images = input_images[batch_start_idx:batch_end_idx]
        
        for filename in batch_input_images:
            input_path = os.path.join(input_dir, filename)
            try:
                image = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)
                if downsample:
                    image = cv2.resize(image, None, fx=0.5, fy=0.5)
                points = preprocess_image(image, z_scale, allow_negative_z)
                mesh = generate_mesh(points, debug)
                
                # Store mesh and texture
                meshes.append(mesh)
                textures.append(image)
                
                # Determine position based on filename
                filename_parts = filename.split('_')
                x_pos = int(filename_parts[1])
                y_pos = int(filename_parts[2].split('.')[0])
                positions.append((x_pos, y_pos, 0))  # Assuming z=0 for simplicity
                
            except Exception as e:
                print(f"Error processing {filename}: {e}")
    
    # Merge meshes
    merged_mesh = merge_meshes(meshes, textures, positions)
    
    # Convert merged mesh to glTF format
    gltf = convert_open3d_mesh_to_gltf(merged_mesh)
    
    # Write glTF to file
    output_path = os.path.join(output_dir, "merged_mesh.glb")
    with open(output_path, 'wb') as f:
        f.write(gltf.serialize())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate 3D meshes from overhead mini map images")
    parser.add_argument("input_dir", type=str, help="Directory containing input overhead mini map images")
    parser.add_argument("output_dir", type=str, help="Directory to save output glTF 3D meshes")
    parser.add_argument("--downsample", action="store_true", help="Optional flag to downsample input images")
    parser.add_argument("--z_scale", type=float, default=0.0625, help="Optional parameter to scale the Z-axis of the generated meshes")
    parser.add_argument("--debug", action="store_true", help="Optional flag to enable debug mode with verbose output")
    parser.add_argument("--allow_negative_z", action="store_true", help="Optional flag to allow negative Z-axis values in the generated meshes")
    parser.add_argument("--batch_size", type=int, default=1, help="Batch size for processing multiple tiles simultaneously")
    args = parser.parse_args()
    
    main(args.input_dir, args.output_dir, args.downsample, args.z_scale, args.debug, args.allow_negative_z, args.batch_size)
