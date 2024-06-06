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

class WdtAlpha:
    def __init__(self, wdt_alpha_name):
        self.wdt_name = wdt_alpha_name
        self.mver = None
        self.mphd = None
        self.main = None
        self.mdnm = None
        self.monm = None
        self.modf = None

        with open(wdt_alpha_name, 'rb') as f:
            file_content = f.read()

        offset_in_file = 0
        self.mver = self.read_chunk(file_content, offset_in_file)
        offset_in_file += 8 + self.mver.size

        mphd_start_offset = offset_in_file
        self.mphd = self.read_chunk(file_content, offset_in_file)
        offset_in_file += 8 + self.mphd.size

        self.main = self.read_chunk(file_content, offset_in_file)
        offset_in_file += 8 + self.main.size

        mdnm_offset = struct.unpack('<I', self.mphd.data[4:8])[0]
        self.mdnm = self.read_chunk(file_content, mphd_start_offset + mdnm_offset)

        monm_offset = struct.unpack('<I', self.mphd.data[12:16])[0]
        self.monm = self.read_chunk(file_content, mphd_start_offset + monm_offset)

        if self.is_wmo_based():
            self.modf = self.read_chunk(file_content, offset_in_file)
            offset_in_file += 8 + self.modf.size

    def read_chunk(self, file_content, offset):
        chunk_name = file_content[offset:offset + 4].decode('ascii')
        chunk_size = struct.unpack('<I', file_content[offset + 4:offset + 8])[0]
        chunk_data = file_content[offset + 8:offset + 8 + chunk_size]
        return Chunk(name=chunk_name, size=chunk_size, data=chunk_data)

    def is_wmo_based(self):
        return self.mphd and self.mphd.data[0] & 1 == 1

    def toWdt(self):
        return Wdt(self)

    def getExistingAdtsNumbers(self):
        adt_numbers = []
        logging.info(f"Main data length: {len(self.main.data)}")
        for i in range(64 * 64):
            offset = i * 4
            if offset + 4 <= len(self.main.data):
                value = struct.unpack('<I', self.main.data[offset:offset + 4])[0]
                logging.debug(f"Checking main data index {i}: value = {value}")
                if value != 0:
                    adt_numbers.append(i)
        logging.info(f"Found {len(adt_numbers)} existing ADTs")
        return adt_numbers

    def getAdtOffsetsInMain(self):
        adt_offsets = []
        logging.info(f"Main data length: {len(self.main.data)}")
        for i in range(64 * 64):
            offset = i * 4
            if offset + 4 <= len(self.main.data):
                adt_offset = struct.unpack('<I', self.main.data[offset:offset + 4])[0]
                adt_offsets.append(adt_offset)
        logging.info(f"Found {len(adt_offsets)} ADT offsets")
        return adt_offsets

    def getMdnmFileNames(self):
        return []

    def getMonmFileNames(self):
        return []

class Wdt:
    def __init__(self, wdt_alpha):
        self.mver = wdt_alpha.mver
        self.mphd = wdt_alpha.mphd
        self.main = wdt_alpha.main
        self.mdnm = wdt_alpha.mdnm
        self.monm = wdt_alpha.monm
        self.modf = wdt_alpha.modf

    def toFile(self, file_name):
        whole_wdt = b''
        if self.mver:
            whole_wdt += self.mver.getWholeChunk()
        if self.mphd:
            whole_wdt += self.mphd.getWholeChunk()
        if self.main:
            whole_wdt += self.main.getWholeChunk()
        if self.mdnm:
            whole_wdt += self.mdnm.getWholeChunk()
        if self.monm:
            whole_wdt += self.monm.getWholeChunk()
        if self.modf:
            whole_wdt += self.modf.getWholeChunk()

        logging.info(f"Writing {len(whole_wdt)} bytes to {file_name}")

        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        with open(file_name, 'wb') as f:
            f.write(whole_wdt)

class AdtAlpha:
    def __init__(self, wdt_alpha_name, offset_in_file, adt_num):
        self.adt_number = adt_num
        self.adt_file_name = self.get_adt_file_name(wdt_alpha_name)
        self.mhdr = None
        self.mcin = None
        self.mtex = None
        self.mddf = None
        self.modf = None
        self.mcnks_alpha = []

        with open(wdt_alpha_name, 'rb') as f:
            file_content = f.read()

        self.mhdr = self.read_chunk(file_content, offset_in_file)
        mhdr_start_offset = offset_in_file + 8

        mcin_offset = struct.unpack('<I', self.mhdr.data[0:4])[0]
        self.mcin = self.read_chunk(file_content, mhdr_start_offset + mcin_offset)

        mtex_offset = struct.unpack('<I', self.mhdr.data[4:8])[0]
        self.mtex = self.read_chunk(file_content, mhdr_start_offset + mtex_offset)

        mddf_offset = struct.unpack('<I', self.mhdr.data[12:16])[0]
        self.mddf = self.read_chunk(file_content, mhdr_start_offset + mddf_offset)

        modf_offset = struct.unpack('<I', self.mhdr.data[20:24])[0]
        self.modf = self.read_chunk(file_content, mhdr_start_offset + modf_offset)

        mcnk_offsets = self.get_mcnk_offsets(self.mcin.data)
        for current_mcnk in range(256):
            offset_in_file = mcnk_offsets[current_mcnk]
            self.mcnks_alpha.append(self.read_chunk(file_content, offset_in_file))

    def read_chunk(self, file_content, offset):
        chunk_name = file_content[offset:offset + 4].decode('ascii')
        chunk_size = struct.unpack('<I', file_content[offset + 4:offset + 8])[0]
        chunk_data = file_content[offset + 8:offset + 8 + chunk_size]
        return Chunk(name=chunk_name, size=chunk_size, data=chunk_data)

    def get_mcnk_offsets(self, mcin_data):
        offsets = []
        for i in range(256):
            offset = struct.unpack('<I', mcin_data[i * 16:(i * 16) + 4])[0]
            offsets.append(offset)
        return offsets

    def get_adt_file_name(self, wdt_name):
        adt_file_name = wdt_name[:-4] + f"_{self.get_x_coord()}_{self.get_y_coord()}.adt"
        return adt_file_name

    def get_x_coord(self):
        return self.adt_number % 64

    def get_y_coord(self):
        return self.adt_number // 64

    def to_adt_lk(self, mdnm_files_names, monm_files_names):
        return AdtLk(self)

class AdtLk:
    def __init__(self, adt_alpha):
        self.mhdr = adt_alpha.mhdr
        self.mcin = adt_alpha.mcin
        self.mtex = adt_alpha.mtex
        self.mddf = adt_alpha.mddf
        self.modf = adt_alpha.modf
        self.mcnks = adt_alpha.mcnks_alpha

    def to_file(self, file_name):
        whole_adt = b''
        if self.mhdr:
            whole_adt += self.mhdr.getWholeChunk()
        if self.mcin:
            whole_adt += self.mcin.getWholeChunk()
        if self.mtex:
            whole_adt += self.mtex.getWholeChunk()
        if self.mddf:
            whole_adt += self.mddf.getWholeChunk()
        if self.modf:
            whole_adt += self.modf.getWholeChunk()

        for mcnk in self.mcnks:
            whole_adt += mcnk.getWholeChunk()

        logging.info(f"Writing {len(whole_adt)} bytes to {file_name}")

        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        with open(file_name, 'wb') as f:
            f.write(whole_adt)

def read_chunk(file_content, offset):
    chunk_name = file_content[offset:offset + 4].decode('ascii')
    chunk_size = struct.unpack('<I', file_content[offset + 4:offset + 8])[0]
    chunk_data = file_content[offset + 8:offset + 8 + chunk_size]
    return Chunk(name=chunk_name, size=chunk_size, data=chunk_data)

def parse_old_wdt(file_content):
    # Start parsing the new WDT format contained in the old WDT
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

def convert_wdt_to_adts(input_file, output_directory):
    with open(input_file, 'rb') as f:
        file_content = f.read()

    # Parse the old WDT file
    chunks = parse_old_wdt(file_content)
    
    # Determine where the new WDT ends
    wdt_end_offset = sum(8 + chunk.size for chunk in chunks)
    
    # Extract ADT positions from the old WDT file
    adt_positions = extract_adt_positions(file_content, wdt_end_offset)

    # Write out the ADT files
    write_adt_files(file_content, adt_positions, output_directory)

    log_file = os.path.join(output_directory, 'log.json')
    with open(log_file, 'w') as log:
        json.dump([chunk.to_dict() for chunk in chunks], log, indent=4)

    logging.info(f"Log written to {log_file}")

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Convert WDT file from old to new format.')
parser.add_argument('input_file', type=str, help='Path to the input old-style WDT file')
parser.add_argument('output_directory', type=str, help='Directory to output new-style ADT files')

args = parser.parse_args()

convert_wdt_to_adts(args.input_file, args.output_directory)
