import argparse
import base64
import os
import numpy as np
from pygltflib import GLTF2, Buffer, BufferView, Accessor, Mesh, Node, Scene, Primitive, Asset

# Import the parse function from the parser.py file
from parser import parse_wlw_or_wlm_file

SCALE_FACTOR = 17066.666

def create_gltf_mesh(parsed_data):
    vertices = []
    uvs = []
    indices = []
    
    index = 0
    for block in parsed_data['blocks']:
        for vertex in block['vertices']:
            scaled_vertex = [coord / SCALE_FACTOR for coord in vertex]
            vertices.extend(scaled_vertex)
            uvs.extend([0, 0])  # Placeholder UVs, can be replaced with real data if available

        # Generate indices for quads (two triangles per quad)
        indices.extend([index, index + 1, index + 2, index + 2, index + 3, index])
        index += 4  # Increment index by 4 for the next block

    vertices = np.array(vertices, dtype=np.float32)
    uvs = np.array(uvs, dtype=np.float32)
    indices = np.array(indices, dtype=np.uint32)
    
    vertex_buffer_data = vertices.tobytes()
    uv_buffer_data = uvs.tobytes()
    index_buffer_data = indices.tobytes()

    return vertex_buffer_data, uv_buffer_data, index_buffer_data, len(vertices) // 3, len(indices)

def export_to_gltf(parsed_data, output_path):
    vertex_buffer_data, uv_buffer_data, index_buffer_data, vertex_count, index_count = create_gltf_mesh(parsed_data)
    
    # Combine all buffers into one and encode as base64
    combined_buffer_data = vertex_buffer_data + uv_buffer_data + index_buffer_data
    encoded_buffer_data = base64.b64encode(combined_buffer_data).decode('ascii')
    
    buffer = Buffer(uri=f"data:application/octet-stream;base64,{encoded_buffer_data}", byteLength=len(combined_buffer_data))
    bufferView_vertex = BufferView(buffer=0, byteOffset=0, byteLength=len(vertex_buffer_data), target=34962)
    bufferView_uv = BufferView(buffer=0, byteOffset=len(vertex_buffer_data), byteLength=len(uv_buffer_data), target=34962)
    bufferView_index = BufferView(buffer=0, byteOffset=len(vertex_buffer_data + uv_buffer_data), byteLength=len(index_buffer_data), target=34963)
    
    accessor_vertex = Accessor(bufferView=0, byteOffset=0, componentType=5126, count=vertex_count, type="VEC3")
    accessor_uv = Accessor(bufferView=1, byteOffset=0, componentType=5126, count=vertex_count, type="VEC2")
    accessor_index = Accessor(bufferView=2, byteOffset=0, componentType=5125, count=index_count, type="SCALAR")
    
    mesh = Mesh(primitives=[Primitive(attributes={"POSITION": 0, "TEXCOORD_0": 1}, indices=2)])
    
    gltf = GLTF2(
        buffers=[buffer],
        bufferViews=[bufferView_vertex, bufferView_uv, bufferView_index],
        accessors=[accessor_vertex, accessor_uv, accessor_index],
        meshes=[mesh],
        nodes=[Node(mesh=0)],
        scenes=[Scene(nodes=[0])],
        asset=Asset(version="2.0")
    )
    
    gltf.save(output_path)

def process_directory(input_directory, output_directory, combine=False):
    os.makedirs(output_directory, exist_ok=True)
    combined_data = {
        'blocks': [],
        'blocks2': []
    }

    for filename in os.listdir(input_directory):
        file_path = os.path.join(input_directory, filename)
        if os.path.isfile(file_path):
            parsed_data = parse_wlw_or_wlm_file(file_path)
            if combine:
                combined_data['blocks'].extend(parsed_data['blocks'])
                combined_data['blocks2'].extend(parsed_data['blocks2'])
            else:
                output_path = os.path.join(output_directory, f"{os.path.splitext(filename)[0]}.gltf")
                export_to_gltf(parsed_data, output_path)
    
    if combine:
        output_path = os.path.join(output_directory, "combined.gltf")
        export_to_gltf(combined_data, output_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse WLW/WLM files and export to glTF.")
    parser.add_argument('input_path', help="Path to a file or directory to parse.")
    parser.add_argument('output_directory', help="Directory to save the glTF files.")
    parser.add_argument('--combine', action='store_true', help="Combine all parsed files into a single glTF file.")

    args = parser.parse_args()

    if os.path.isdir(args.input_path):
        process_directory(args.input_path, args.output_directory, args.combine)
    else:
        parsed_data = parse_wlw_or_wlm_file(args.input_path)
        output_path = os.path.join(args.output_directory, "output.gltf")
        export_to_gltf(parsed_data, output_path)
