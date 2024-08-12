import os
import argparse
import cv2
import numpy as np
import open3d as o3d
from tqdm import tqdm
from pygltflib import GLTF2, Buffer, BufferView, Accessor, Mesh, Primitive, Image, Texture, Sampler

def preprocess_image(image, z_scale=0.0625):
    # Convert image to point cloud
    depth = np.where(image > 0, image, 0).astype(np.float32)
    points = []
    for y in range(depth.shape[0]):
        for x in range(depth.shape[1]):
            z = max(depth[y, x] * z_scale, 0)  # Ensure non-negative Z-axis values
            points.append([-x, y, -z])  # Flip X-axis
    return points, depth  # Return both points and the depth image

def generate_mesh(points, texture_image, debug=False):
    try:
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
        
        return mesh, texture_image
    except Exception as e:
        print(f"Error generating mesh: {e}")
        return None, None

def write_gltf(output_path, mesh, texture_image):
    try:
        # Convert mesh to glTF format
        gltf = GLTF2()
        buffer = Buffer()
        buffer_view = BufferView(buffer)
        indices = np.array(mesh.triangles).astype(np.uint16)
        vertices = np.array(mesh.vertices).astype(np.float32)
        tex_coords = np.zeros((len(vertices), 2)).astype(np.float32)  # Dummy texture coordinates
        
        # Set indices accessor
        indices_accessor = Accessor(buffer_view, Accessor.UNSIGNED_SHORT, Accessor.INDEX)
        indices_accessor.set_array(indices.flatten())
        indices_accessor.byte_offset = 0
        gltf.add_accessor(indices_accessor)
        
        # Set vertices accessor
        vertices_accessor = Accessor(buffer_view, Accessor.FLOAT_VEC3, Accessor.POSITION)
        vertices_accessor.set_array(vertices.flatten())
        vertices_accessor.byte_offset = len(indices_accessor.array) * 2
        gltf.add_accessor(vertices_accessor)
        
        # Set texture coordinates accessor
        tex_coords_accessor = Accessor(buffer_view, Accessor.FLOAT_VEC2, Accessor.TEXCOORD_0)
        tex_coords_accessor.set_array(tex_coords.flatten())
        tex_coords_accessor.byte_offset = len(indices_accessor.array) * 2 + len(vertices_accessor.array) * 4
        gltf.add_accessor(tex_coords_accessor)
        
        # Set buffer and buffer views
        buffer.add_buffer_view(buffer_view)
        gltf.add_buffer(buffer)
        
        # Create mesh object
        mesh_obj = Mesh()
        primitive = Primitive()
        primitive.indices_accessor = indices_accessor
        primitive.attributes['POSITION'] = vertices_accessor
        primitive.attributes['TEXCOORD_0'] = tex_coords_accessor
        mesh_obj.add_primitive(primitive)
        gltf.add_mesh(mesh_obj)
        
        # Create image object
        image_obj = Image()
        image_obj.set_image(texture_image)
        gltf.add_image(image_obj)
        
        # Create texture object
        texture = Texture()
        texture.source = image_obj
        gltf.add_texture(texture)
        
        # Set sampler
        sampler = Sampler()
        sampler.mag_filter = Sampler.LINEAR
        sampler.min_filter = Sampler.LINEAR
        sampler.wrap_s = Sampler.REPEAT
        sampler.wrap_t = Sampler.REPEAT
        gltf.add_sampler(sampler)
        
        # Set texture and sampler for the primitive
        primitive.material = {
            'baseColorTexture': texture,
            'baseColorSampler': sampler
        }
        
        # Write glTF to file
        with open(output_path, 'wb') as f:
            f.write(gltf.serialize())
        
        return True
    except Exception as e:
        print(f"Error writing glTF: {e}")
        return False

def main(input_dir, output_dir, downsample=False, z_scale=0.0625, debug=False, batch_size=1):
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
            output_filename = f"mesh_{filename[:-4]}.glb"
            output_path = os.path.join(output_dir, output_filename)
            
            try:
                image = cv2.imread(input_path, cv2.IMREAD_COLOR)
                if downsample:
                    image = cv2.resize(image, None, fx=0.5, fy=0.5)
                points, texture_image = preprocess_image(image, z_scale)
                mesh, texture_image = generate_mesh(points, texture_image, debug)
                if mesh and texture_image:
                    success = write_gltf(output_path, mesh, texture_image)
                    if debug and success:
                        print(f"Saved {output_path}")
            except Exception as e:
                print(f"Error processing {filename}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate 3D meshes from overhead mini map images")
    parser.add_argument("input_dir", type=str, help="Directory containing input overhead mini map images")
    parser.add_argument("output_dir", type=str, help="Directory to save output glTF 3D meshes")
    parser.add_argument("--downsample", action="store_true", help="Optional flag to downsample input images")
    parser.add_argument("--z_scale", type=float, default=0.0625, help="Optional parameter to scale the Z-axis of the generated meshes")
    parser.add_argument("--debug", action="store_true", help="Optional flag to enable debug mode with verbose output")
    parser.add_argument("--batch_size", type=int, default=1, help="Batch size for processing multiple tiles simultaneously")
    args = parser.parse_args()
    
    main(args.input_dir, args.output_dir, args.downsample, args.z_scale, args.debug, args.batch_size)
