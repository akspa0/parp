import struct
import os
import logging
import json
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Chunk:
    def __init__(self, name="", size=0, data=None):
        self.name = name
        self.size = size
        self.data = data if data else b''

    def getWholeChunk(self):
        name_bytes = self.name.encode('ascii')
        size_bytes = struct.pack('<I', self.size)
        return name_bytes + size_bytes + self.data

    def to_dict(self):
        return {
            'name': self.name,
            'size': self.size,
            'data_length': len(self.data)
        }

    def __repr__(self):
        return f"Chunk(name='{self.name}', size={self.size}, data_length={len(self.data)})"

def read_chunk(file_content, offset):
    chunk_name = file_content[offset:offset + 4].decode('ascii')
    chunk_size = struct.unpack('<I', file_content[offset + 4:offset + 8])[0]
    chunk_data = file_content[offset + 8:offset + 8 + chunk_size]
    return Chunk(name=chunk_name, size=chunk_size, data=chunk_data)

def parse_new_wdt(file_path):
    with open(file_path, 'rb') as f:
        file_content = f.read()

    offset = 0
    chunks = []

    while offset < len(file_content):
        chunk = read_chunk(file_content, offset)
        chunks.append(chunk)
        offset += 8 + chunk.size

    return chunks

def parse_old_wdt(file_content):
    offset_in_file = 0
    chunks = []

    while offset_in_file < len(file_content):
        try:
            chunk = read_chunk(file_content, offset_in_file)
            chunks.append(chunk)
            offset_in_file += 8 + chunk.size
        except Exception as e:
            logging.error(f"Failed to parse chunk at offset {offset_in_file}: {e}")
            break

    logging.info(f"Parsed {len(chunks)} chunks from the old WDT file")
    return chunks

def extract_adt_positions(file_content, wdt_end_offset):
    adt_positions = []
    offset = wdt_end_offset

    while offset < len(file_content):
        try:
            chunk_name = file_content[offset:offset + 4].decode('ascii')
            logging.debug(f"Reading chunk at offset {offset}: chunk_name = {chunk_name}")
            if chunk_name == 'ADT ':
                adt_positions.append(offset)
            chunk_size = struct.unpack('<I', file_content[offset + 4:offset + 8])[0]
            offset += 8 + chunk_size
        except Exception as e:
            logging.error(f"Failed to read ADT position at offset {offset}: {e}")
            break

    logging.info(f"Found {len(adt_positions)} ADT positions")
    return adt_positions

def write_adt_files(file_content, adt_positions, output_directory):
    for i, adt_offset in enumerate(adt_positions):
        chunk = read_chunk(file_content, adt_offset)
        adt_data = chunk.getWholeChunk()

        x = i % 64
        y = i // 64
        output_file = os.path.join(output_directory, f"output_{x:02d}_{y:02d}.adt")
        
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'wb') as f:
            f.write(adt_data)

        logging.info(f"Created {output_file} with size {os.path.getsize(output_file)} bytes")

def convert_wdt_to_adts(input_file, output_directory, new_wdt_file_path):
    os.makedirs(output_directory, exist_ok=True)

    with open(input_file, 'rb') as f:
        file_content = f.read()

    # Parse the old WDT file
    old_chunks = parse_old_wdt(file_content)
    
    # Determine where the new WDT ends
    wdt_end_offset = sum(8 + chunk.size for chunk in old_chunks if chunk.name != 'DMAP')
    
    # Extract ADT positions from the old WDT file
    adt_positions = extract_adt_positions(file_content, wdt_end_offset)

    # Write out the ADT files
    write_adt_files(file_content, adt_positions, output_directory)

    # Parse and log the new WDT file
    new_wdt_chunks = parse_new_wdt(new_wdt_file_path)

    # Mapping old chunks to new chunks (Example - Update as per actual mapping logic)
    mapping = {
        'MWMO': 'MWMO', # Example mapping
        'MODF': 'MODF', # Example mapping
        'MAIN': 'MAIN'  # Example mapping
    }

    mapped_chunks = []
    for old_chunk in old_chunks:
        new_chunk_name = mapping.get(old_chunk.name)
        if new_chunk_name:
            mapped_chunk = Chunk(name=new_chunk_name, size=old_chunk.size, data=old_chunk.data)
            mapped_chunks.append(mapped_chunk)

    # Save the analysis log to a JSON file
    log_file = os.path.join(output_directory, 'analysis_log.json')
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    with open(log_file, 'w') as log:
        json.dump({
            'old_chunks': [chunk.to_dict() for chunk in old_chunks],
            'new_wdt_chunks': [chunk.to_dict() for chunk in new_wdt_chunks],
            'mapped_chunks': [chunk.to_dict() for chunk in mapped_chunks]
        }, log, indent=4)

    logging.info(f"Log written to {log_file}")

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Convert WDT file from old to new format.')
parser.add_argument('input_file', type=str, help='Path to the input old-style WDT file')
parser.add_argument('output_directory', type=str, help='Directory to output new-style ADT files')
parser.add_argument('new_wdt_file_path', type=str, help='Path to the new format WDT file')

args = parser.parse_args()

convert_wdt_to_adts(args.input_file, args.output_directory, args.new_wdt_file_path)
