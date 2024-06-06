import struct
import argparse
import os
import json

# Define the Chunk class
class Chunk:
    def __init__(self, name="", size=0, data=None):
        self.name = name
        self.size = size
        self.data = data if data else []

    def getWholeChunk(self):
        name_bytes = self.name.encode('ascii')
        size_bytes = struct.pack('<I', self.size)
        return list(name_bytes) + list(size_bytes) + self.data

    def getOffset(self, offset):
        return 0

    def to_dict(self):
        return {
            'name': self.name,
            'size': self.size,
            'data_length': len(self.data)
        }

    def __repr__(self):
        return f"Chunk(name='{self.name}', size={self.size}, data_length={len(self.data)})"

# Function to parse the chunks from the file content
def parse_chunks(file_content):
    index = 0
    chunks = []
    while index < len(file_content):
        chunk_name = file_content[index:index+4].decode('ascii')
        chunk_size = struct.unpack('<I', file_content[index+4:index+8])[0]
        chunk_data = file_content[index+8:index+8+chunk_size]
        chunk = Chunk(name=chunk_name, size=chunk_size, data=list(chunk_data))
        chunks.append(chunk)
        index += 8 + chunk_size
    return chunks

class AdtAlpha:
    def __init__(self, adtNumber, x, y):
        self.adtNumber = adtNumber
        self.x = x
        self.y = y
        self.mhdr = Chunk("MHDR", 64, [0]*64)
        self.mcin = Chunk("MCIN", 4096, [0]*4096)
        self.mtex = Chunk("MTEX", 0, [])
        self.mddf = Chunk("MDDF", 0, [])
        self.modf = Chunk("MODF", 0, [])
        self.mcnksAlpha = []

    def toFile(self, fileName):
        wholeAdt = []
        if self.mhdr:
            wholeAdt.extend(self.mhdr.getWholeChunk())
        if self.mcin:
            wholeAdt.extend(self.mcin.getWholeChunk())
        if self.mtex:
            wholeAdt.extend(self.mtex.getWholeChunk())
        if self.mddf:
            wholeAdt.extend(self.mddf.getWholeChunk())
        if self.modf:
            wholeAdt.extend(self.modf.getWholeChunk())

        for mcnk in self.mcnksAlpha:
            wholeAdt.extend(mcnk.getWholeChunk())

        # Debug: Print the length of data being written
        print(f"Writing {len(wholeAdt)} bytes to {fileName}")

        with open(fileName, 'wb') as f:
            f.write(bytearray(wholeAdt))

class AdtLk:
    def __init__(self, chunks):
        self.mhdr = next((chunk for chunk in chunks if chunk.name == 'MHDR'), None)
        self.mcin = next((chunk for chunk in chunks if chunk.name == 'MCIN'), None)
        self.mtex = next((chunk for chunk in chunks if chunk.name == 'MTEX'), None)
        self.mddf = next((chunk for chunk in chunks if chunk.name == 'MDDF'), None)
        self.modf = next((chunk for chunk in chunks if chunk.name == 'MODF'), None)
        self.mcnks = [chunk for chunk in chunks if chunk.name == 'MCNK' or chunk.name == 'KNCM']

    def toAdtAlpha(self, adtNumber, x, y):
        adtAlpha = AdtAlpha(adtNumber, x, y)
        adtAlpha.mhdr = self.convertMhdrToAlpha()
        adtAlpha.mcin = self.convertMcinToAlpha()
        adtAlpha.mtex = self.convertMtexToAlpha()
        adtAlpha.mddf = self.convertMddfToAlpha()
        adtAlpha.modf = self.convertModfToAlpha()
        adtAlpha.mcnksAlpha = self.convertMcnksToAlpha()
        return adtAlpha

    def convertMhdrToAlpha(self):
        alpha_mhdr = Chunk("MHDR", 64, self.mhdr.data if self.mhdr else [0]*64)
        return alpha_mhdr

    def convertMcinToAlpha(self):
        alpha_mcin = Chunk("MCIN", 4096, self.mcin.data if self.mcin else [0]*4096)
        return alpha_mcin

    def convertMtexToAlpha(self):
        alpha_mtex = Chunk("MTEX", len(self.mtex.data) if self.mtex else 0, self.mtex.data if self.mtex else [])
        return alpha_mtex

    def convertMddfToAlpha(self):
        alpha_mddf = Chunk("MDDF", len(self.mddf.data) if self.mddf else 0, self.mddf.data if self.mddf else [])
        return alpha_mddf

    def convertModfToAlpha(self):
        alpha_modf = Chunk("MODF", len(self.modf.data) if self.modf else 0, self.modf.data if self.modf else [])
        return alpha_modf

    def convertMcnksToAlpha(self):
        alpha_mcnks = []
        for mcnk in self.mcnks:
            alpha_mcnks.append(Chunk("MCNK", len(mcnk.data), mcnk.data))
        return alpha_mcnks

def convert_wdt_to_adts(input_file, output_directory):
    with open(input_file, 'rb') as f:
        file_content = f.read()

    parsed_chunks = parse_chunks(file_content)
    chunk_dicts = [chunk.to_dict() for chunk in parsed_chunks]

    mcnk_chunks = [chunk for chunk in parsed_chunks if chunk.name == 'KNCM']
    adt_count = min(len(mcnk_chunks) // 256, 64 * 64)

    os.makedirs(output_directory, exist_ok=True)

    for i in range(adt_count):
        x = i % 64
        y = i // 64
        adt_number = i
        adt_alpha = AdtAlpha(adt_number, x, y)
        adt_alpha.mhdr = next((chunk for chunk in parsed_chunks if chunk.name == 'MHDR'), adt_alpha.mhdr)
        adt_alpha.mcin = next((chunk for chunk in parsed_chunks if chunk.name == 'MCIN'), adt_alpha.mcin)
        adt_alpha.mtex = next((chunk for chunk in parsed_chunks if chunk.name == 'MTEX'), adt_alpha.mtex)
        adt_alpha.mddf = next((chunk for chunk in parsed_chunks if chunk.name == 'MDDF'), adt_alpha.mddf)
        adt_alpha.modf = next((chunk for chunk in parsed_chunks if chunk.name == 'MODF'), adt_alpha.modf)

        # Collect 256 MCNK chunks for the current ADT file
        adt_alpha.mcnksAlpha = mcnk_chunks[i*256:(i+1)*256]

        output_file = os.path.join(output_directory, f"output_{x:02d}_{y:02d}.adt")
        adt_alpha.toFile(output_file)

        # Debug: Log the created file and its size
        print(f"Created {output_file} with size {os.path.getsize(output_file)} bytes")

    log_file = os.path.join(output_directory, 'log.json')
    with open(log_file, 'w') as log:
        json.dump(chunk_dicts, log, indent=4)

    print(f"Log written to {log_file}")

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Convert WDT file from old to new format.')
parser.add_argument('input_file', type=str, help='Path to the input old-style WDT file')
parser.add_argument('output_directory', type=str, help='Directory to output new-style ADT files')

args = parser.parse_args()

convert_wdt_to_adts(args.input_file, args.output_directory)
