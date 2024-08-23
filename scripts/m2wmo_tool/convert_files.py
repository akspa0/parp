import os
import struct
import argparse
from wmo_v14 import WMOv14Parser
from mdx_to_m2 import MDXtoM2Converter

def save_wmo(filepath, wmo):
    with open(filepath, 'wb') as f:
        f.write(struct.pack('4s', wmo.magic.encode('utf-8')))
        f.write(struct.pack('I', 17))  # Write the version as 17
        for chunk_id, chunk_size, chunk_data in wmo.chunks:
            f.write(struct.pack('4sI', chunk_id, chunk_size))
            f.write(chunk_data)

def save_mdx(filepath, mdx):
    with open(filepath, 'wb') as f:
        f.write(struct.pack('4s', mdx.magic.encode('utf-8')))
        f.write(struct.pack('I', 1300))  # Write the version as 1300
        for chunk_id, chunk_size, chunk_data in mdx.chunks:
            f.write(struct.pack('4sI', chunk_id, chunk_size))
            f.write(chunk_data)

def convert_wmo(input_path, output_path):
    wmo_parser = WMOv14Parser(input_path)
    wmo_parser.read()
    wmo_parser.parse_chunks()
    wmo_parser.convert_to_v17()
    save_wmo(output_path, wmo_parser)
    print(f"Converted WMO v14 file saved as WMO v17 at {output_path}")

def convert_mdx(input_path, output_path):
    mdx_converter = MDXtoM2Converter(input_path)
    mdx_converter.read()
    mdx_converter.parse_chunks()
    mdx_converter.convert_to_m2()
    mdx_converter.save_m2(output_path)
    print(f"Converted MDX file saved as M2 at {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Convert MDX and WMO files to their modern counterparts.")
    parser.add_argument('input_path', type=str, help="Path to the input folder containing MDX and WMO files.")
    parser.add_argument('output_path', type=str, help="Path to the output folder where converted files will be saved.")
    parser.add_argument('--type', type=str, choices=['mdx', 'wmo', 'all'], default='all', 
                        help="Type of files to convert: 'mdx' for MDX files, 'wmo' for WMO files, or 'all' for both.")
    args = parser.parse_args()

    input_path = args.input_path
    output_path = args.output_path

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    for filename in os.listdir(input_path):
        if args.type in ['mdx', 'all'] and filename.endswith('.mdx'):
            convert_mdx(os.path.join(input_path, filename), os.path.join(output_path, filename.replace('.mdx', '.m2')))
        elif args.type in ['wmo', 'all'] and filename.endswith('.wmo'):
            convert_wmo(os.path.join(input_path, filename), os.path.join(output_path, filename.replace('.wmo', '_v17.wmo')))

if __name__ == "__main__":
    main()
