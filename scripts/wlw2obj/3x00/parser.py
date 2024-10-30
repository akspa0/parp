import argparse
import os
import json
import struct

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
        magic = magic.hex()  # Convert bytes to a hex string for JSON serialization
        if is_wlm:
            liquid_type = 6  # For WLM files, liquidType is always 6 (Magma)
        result = {
            'magic': magic,  # Keep as hex string
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
                result['blocks'].append({
                    'vertices': vertices, 
                    'coord': coord, 
                    'data': [int(d) for d in block_data]  # Convert to list of ints for JSON serialization
                })
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
                    _unk14 = data[offset:offset+56].hex()  # Convert bytes to hex string for JSON serialization
                    offset += 56
                    result['blocks2'].append({
                        '_unk00': _unk00, 
                        '_unk0C': _unk0C, 
                        '_unk14': _unk14
                    })
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

def process_directory(input_directory, output_directory):
    os.makedirs(output_directory, exist_ok=True)

    for filename in os.listdir(input_directory):
        file_path = os.path.join(input_directory, filename)
        if os.path.isfile(file_path):
            parsed_data = parse_wlw_or_wlm_file(file_path)
            output_path = os.path.join(output_directory, f"{os.path.splitext(filename)[0]}.json")
            with open(output_path, 'w') as f:
                json.dump(parsed_data, f, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse WLW/WLM files and export to JSON.")
    parser.add_argument('input_path', help="Path to a file or directory to parse.")
    parser.add_argument('output_directory', help="Directory to save the JSON files.")

    args = parser.parse_args()

    if os.path.isdir(args.input_path):
        process_directory(args.input_path, args.output_directory)
    else:
        parsed_data = parse_wlw_or_wlm_file(args.input_path)
        output_path = os.path.join(args.output_directory, "output.json")
        with open(output_path, 'w') as f:
            json.dump(parsed_data, f, indent=4)
