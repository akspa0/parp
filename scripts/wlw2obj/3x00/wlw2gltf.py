import argparse
import os
import struct
import numpy as np
from pygltflib import GLTF2, Buffer, BufferView, Accessor, Mesh, Node, Scene, Primitive, Asset

# Mapping liquid types to human-readable strings and corresponding texture files
LIQUID_TYPE_MAPPING = {
    0: ('still', 'Blue_1.png'),
    1: ('ocean', 'Blue_1.png'),
    2: ('?', 'Yellow_1.png'),
    3: ('slime', 'Green_1.png'),
    4: ('river', 'WaterBlue_1.png'),
    6: ('magma', 'Red_1.png'),
    8: ('fast flowing', 'Charcoal_1.png')
}

def parse_wlw_or_wlm_file(file_path, is_wlm=False, verbose=False):
    """Parses a WLW or WLM file and extracts informative data."""
    if verbose:
        print(f"Parsing file: {file_path}")

    with open(file_path, 'rb') as file:
        data = file.read()

        # Read header
        magic, version, unk06, liquid_type, padding, block_count = struct.unpack('4sHHHHI', data[:16])
        # magic = magic.decode('utf-8')  # Removing decoding to avoid errors
        if is_wlm:
            liquid_type = 6  # For WLM files, liquidType is always 6 (Magma)
        result = {
            'magic': magic,  # Keeping as bytes
            'version': version,
            'unk06': unk06,
            'liquid_type': liquid_type,
            'liquid_type_str': LIQUID_TYPE_MAPPING.get(liquid_type, ('unknown', 'Yellow_1.png'))[0],
            'texture': LIQUID_TYPE_MAPPING.get(liquid_type, ('unknown', 'Yellow_1.png'))[1],
            'padding': padding,
            'block_count': block_count,
            'blocks': [],
            'block2_count': None,
            'blocks2': [],
            'unknown': None
        }
        offset = 16

        # Read blocks
        for _ in range(block_count):
            if offset + 48*4 + 2*4 + 80*2 > len(data):
                break
            try:
                vertices = [struct.unpack('3f', data[offset + i*12 : offset + (i+1)*12]) for i in range(16)]
                offset += 48*4
                coord = struct.unpack('2f', data[offset:offset+2*4])
                offset += 2*4
                block_data = struct.unpack('80H', data[offset:offset+80*2])
                offset += 80*2
                result['blocks'].append({'vertices': vertices, 'coord': coord, 'data': block_data})
            except struct.error as e:
                print(f"Error unpacking block at offset {offset}: {e}")
                break
            if offset >= len(data):
                break

        # Read block2 if present
        if offset + 4 <= len(data):
            block2_count, = struct.unpack('I', data[offset:offset+4])
            offset += 4
            result['block2_count'] = block2_count
            for _ in range(block2_count):
                if offset + 3*4 + 2*4 + 56 > len(data):
                    break
                try:
                    _unk00 = struct.unpack('3f', data[offset:offset+3*4])
                    offset += 3*4
                    _unk0C = struct.unpack('2f', data[offset:offset+2*4])
                    offset += 2*4
                    _unk14 = struct.unpack('56s', data[offset:offset+56])
                    offset += 56
                    result['blocks2'].append({'_unk00': _unk00, '_unk0C': _unk0C, '_unk14': _unk14})
                except struct.error as e:
                    print(f"Error unpacking block2 at offset {offset}: {e}")
                    break

        # Read unknown if version ≥ 1
        if version >= 1 and offset < len(data):
            unknown, = struct.unpack('B', data[offset:offset+1])
            result['unknown'] = unknown

    if verbose:
        print(f"Finished parsing file: {file_path}")
    return result

def create_gltf_mesh(parsed_data):
    vertices = []
    for block in parsed_data['blocks']:
        for vertex in block['vertices']:
            vertices.extend(vertex)

    buffer_data = np.array(vertices, dtype=np.float32).tobytes()
    
    return buffer_data, vertices

def export_to_gltf(parsed_data, output_path):
    buffer_data, vertices = create_gltf_mesh(parsed_data)
    
    buffer_filename = os.path.splitext(output_path)[0] + "_buffer.bin"
    with open(buffer_filename, 'wb') as f:
        f.write(buffer_data)
    
    buffer = Buffer(uri=os.path.basename(buffer_filename), byteLength=len(buffer_data))
    bufferView = BufferView(buffer=0, byteOffset=0, byteLength=len(buffer_data))
    accessor = Accessor(bufferView=0, byteOffset=0, componentType=5126, count=len(vertices)//3, type="VEC3")
    
    mesh = Mesh(primitives=[Primitive(attributes={"POSITION": 0})])
    
    gltf = GLTF2(
        buffers=[buffer],
        bufferViews=[bufferView],
        accessors=[accessor],
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
