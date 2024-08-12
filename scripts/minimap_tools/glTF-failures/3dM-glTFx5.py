import os
import argparse
import cv2
import numpy as np
import open3d as o3d
from tqdm import tqdm
import pygltflib

def preprocess_image(image, z_scale=0.0625):
    # Convert image to grayscale
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply thresholding to generate a binary image
    _, binary_image = cv2.threshold(gray_image, 127, 255, cv2.THRESH_BINARY)
    
    # Convert binary image to float values and scale Z-axis
    float_image = binary_image.astype(float) * z_scale
    
    # Generate points from the thresholded image for mesh generation
    points = []
    for y in range(float_image.shape[0]):
        for x in range(float_image.shape[1]):
            z = float_image[y, x]
            points.append([x, y, z])
    
    return points

def generate_mesh(points):
    # Convert points to Open3D PointCloud
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    
    # Estimate normals
    o3d.geometry.estimate_normals(pcd)
    
    # Generate mesh using Poisson surface reconstruction
    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd)
    
    # Ensure the mesh is properly filled and smooth
    mesh.fill_holes()
    mesh.filter_smooth_laplacian()
    
    return mesh

def export_gltf(mesh, image, output_file):
    # Convert mesh to glTF format
    vertices = np.asarray(mesh.vertices)
    indices = np.asarray(mesh.triangles)
    normals = np.asarray(mesh.vertex_normals)
    
    # Create glTF buffer and accessor for vertices
    vertices_data = np.array(vertices, dtype=np.float32).tobytes()
    vertices_buffer = pygltflib.Buffer(uri="buffer_vertices.bin")
    vertices_buffer_view = pygltflib.BufferView(buffer=0, byteOffset=0, byteLength=len(vertices_data), target=pygltflib.BufferTarget.ARRAY_BUFFER)
    vertices_accessor = pygltflib.Accessor(
        bufferView=0,
        componentType=pygltflib.GLTFComponentType.FLOAT,
        type=pygltflib.GLTFType.VEC3,
        count=len(vertices)
    )

    # Create glTF buffer and accessor for indices
    indices_data = np.array(indices, dtype=np.uint32).tobytes()
    indices_buffer = pygltflib.Buffer(uri="buffer_indices.bin")
    indices_buffer_view = pygltflib.BufferView(buffer=1, byteOffset=0, byteLength=len(indices_data), target=pygltflib.BufferTarget.ELEMENT_ARRAY_BUFFER)
    indices_accessor = pygltflib.Accessor(
        bufferView=1,
        componentType=pygltflib.GLTFComponentType.UNSIGNED_INT,
        type=pygltflib.GLTFType.SCALAR,
        count=len(indices)
    )

    # Create glTF buffer and accessor for normals
    normals_data = np.array(normals, dtype=np.float32).tobytes()
    normals_buffer = pygltflib.Buffer(uri="buffer_normals.bin")
    normals_buffer_view = pygltflib.BufferView(buffer=2, byteOffset=0, byteLength=len(normals_data), target=pygltflib.BufferTarget.ARRAY_BUFFER)
    normals_accessor = pygltflib.Accessor(
        bufferView=2,
        componentType=pygltflib.GLTFComponentType.FLOAT,
        type=pygltflib.GLTFType.VEC3,
        count=len(normals)
    )

    # Create glTF image
    image_data = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image_uri = "texture_image.png"
    with open(image_uri, "wb") as f:
        f.write(image_data)

    gltf_image = pygltflib.Image(uri=image_uri)

    # Create glTF texture
    texture = pygltflib.Texture(source=0)

    # Create glTF material
    material = pygltflib.Material(pbrMetallicRoughness=pygltflib.PBRMetallicRoughness(baseColorTexture=pygltflib.TextureInfo(index=0)))

    # Create glTF mesh
    mesh = pygltflib.Mesh(
        primitives=[pygltflib.Primitive(
            attributes=pygltflib.Attributes(POSITION=0, NORMAL=2),
            indices=1,
            material=0
        )]
    )

    # Create glTF scene
    scene = pygltflib.Scene(nodes=[0])

    # Create glTF nodes
    node = pygltflib.Node(mesh=0)
    node_matrix = [1, 0, 0, 0, 0, 0, -1, 0, 0, 1, 0, 0, 0, 0, 0, 1]  # Transformation matrix for coordinate system conversion
    node_matrix_accessor = pygltflib.Accessor(
        bufferView=3,
        componentType=pygltflib.GLTFComponentType.FLOAT,
        type=pygltflib.GLTFType.MAT4,
        count=1
    )
    node_matrix_buffer_view = pygltflib.BufferView(buffer=3, byteOffset=0, byteLength=64, target=None)
    node_matrix_buffer = pygltflib.Buffer(uri="buffer_node_matrix.bin")

    # Create glTF JSON
    gltf = pygltflib.GLTF(
        scene=0,
        buffers=[vertices_buffer, indices_buffer, normals_buffer, node_matrix_buffer],
        bufferViews=[vertices_buffer_view, indices_buffer_view, normals_buffer_view, node_matrix_buffer_view],
        accessors=[vertices_accessor, indices_accessor, normals_accessor, node_matrix_accessor],
        images=[gltf_image],
        textures=[texture],
        materials=[material],
        meshes=[mesh],
        scenes=[scene],
        nodes=[node]
    )

    # Write glTF data to file
    gltf.save(output_file)

def process_image(input_file, output_dir, z_scale, skip_gltf, debug):
    # Load image
    image = cv2.imread(input_file)

    # Preprocess image
    points = preprocess_image(image, z_scale)

    # Generate mesh
    mesh = generate_mesh(points)

    # Export to glTF format
    if not skip_gltf:
        output_file = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(input_file))[0]}.glb")
        export_gltf(mesh, image, output_file)
        if debug:
            print("Exporting glTF...")

def main(input_dir, output_dir, downsample, z_scale, debug, batch_size, skip_gltf):
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
            process_image(input_path, output_dir, z_scale, skip_gltf, debug)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate 3D meshes from overhead mini map images")
    parser.add_argument("input_dir", type=str, help="Directory containing input overhead mini map images")
    parser.add_argument("output_dir", type=str, help="Directory to save output glTF 3D mesh files")
    parser.add_argument("--downsample", action="store_true", help="Optional flag to downsample input images")
    parser.add_argument("--z_scale", type=float, default=0.0625, help="Optional parameter to scale the Z-axis of the generated meshes")
    parser.add_argument("--debug", action="store_true", help="Optional flag to enable debug mode with verbose output")
    parser.add_argument("--batch_size", type=int, default=1, help="Batch size for processing multiple tiles simultaneously")
    parser.add_argument("--skip_gltf", action="store_true", help="Disables glTF generation")
    args = parser.parse_args()

    main(args.input_dir, args.output_dir, args.downsample, args.z_scale, args.debug, args.batch_size, args.skip_gltf)
