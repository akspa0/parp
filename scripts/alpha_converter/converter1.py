import struct
import argparse
import os

# Define the Chunk class
class Chunk:
    def __init__(self, name="", size=0, data=None):
        self.name = name
        self.size = size
        self.data = data if data else []

    def getWholeChunk(self):
        return self.data

    def getOffset(self, offset):
        return 0

    def __repr__(self):
        return f"Chunk(name='{self.name}', size={self.size})"

# Function to parse the chunks from the file content
def parse_chunks(file_content):
    index = 0
    chunks = []
    while index < len(file_content):
        # Extract the chunk header (4 bytes for name and 4 bytes for size)
        chunk_name = file_content[index:index+4].decode('ascii')
        chunk_size = struct.unpack('<I', file_content[index+4:index+8])[0]
        chunk_data = file_content[index+8:index+8+chunk_size]
        
        # Create a Chunk instance and add it to the list
        chunk = Chunk(name=chunk_name, size=chunk_size, data=list(chunk_data))
        chunks.append(chunk)
        
        # Move to the next chunk
        index += 8 + chunk_size
    
    return chunks

class AdtAlpha:
    def __init__(self, adtNumber):
        self.adtNumber = adtNumber
        self.mhdr = Chunk()
        self.mcin = Chunk()
        self.mtex = Chunk()
        self.mddf = Chunk()
        self.modf = Chunk()
        self.mcnksAlpha = []

    def toFile(self, fileName):
        wholeAdt = []
        wholeAdt.extend(self.mhdr.getWholeChunk())
        wholeAdt.extend(self.mcin.getWholeChunk())
        wholeAdt.extend(self.mtex.getWholeChunk())
        wholeAdt.extend(self.mddf.getWholeChunk())
        wholeAdt.extend(self.modf.getWholeChunk())

        for mcnk in self.mcnksAlpha:
            wholeAdt.extend(mcnk.getWholeChunk())

        with open(fileName, 'wb') as f:
            f.write(bytearray(wholeAdt))

class AdtLk:
    def __init__(self, chunks):
        # Load the LK ADT chunks
        self.mhdr = next((chunk for chunk in chunks if chunk.name == 'MHDR'), None)
        self.mcin = next((chunk for chunk in chunks if chunk.name == 'MCIN'), None)
        self.mtex = next((chunk for chunk in chunks if chunk.name == 'MTEX'), None)
        self.mddf = next((chunk for chunk in chunks if chunk.name == 'MDDF'), None)
        self.modf = next((chunk for chunk in chunks if chunk.name == 'MODF'), None)
        self.mcnks = [chunk for chunk in chunks if chunk.name == 'MCNK']

    def toAdtAlpha(self, adtNumber):
        adtAlpha = AdtAlpha(adtNumber)
        adtAlpha.mhdr = self.convertMhdrToAlpha()
        adtAlpha.mcin = self.convertMcinToAlpha()
        adtAlpha.mtex = self.convertMtexToAlpha()
        adtAlpha.mddf = self.convertMddfToAlpha()
        adtAlpha.modf = self.convertModfToAlpha()
        adtAlpha.mcnksAlpha = self.convertMcnksToAlpha()
        return adtAlpha

    def convertMhdrToAlpha(self):
        alpha_mhdr = Chunk("MHDR", 64, self.mhdr.data)
        return alpha_mhdr

    def convertMcinToAlpha(self):
        alpha_mcin = Chunk("MCIN", 4096, self.mcin.data)
        return alpha_mcin

    def convertMtexToAlpha(self):
        alpha_mtex = Chunk("MTEX", len(self.mtex.data), self.mtex.data)
        return alpha_mtex

    def convertMddfToAlpha(self):
        alpha_mddf = Chunk("MDDF", len(self.mddf.data), self.mddf.data)
        return alpha_mddf

    def convertModfToAlpha(self):
        alpha_modf = Chunk("MODF", len(self.modf.data), self.modf.data)
        return alpha_modf

    def convertMcnksToAlpha(self):
        alpha_mcnks = []
        for mcnk in self.mcnks:
            alpha_mcnks.append(Chunk("MCNK", len(mcnk.data), mcnk.data))
        return alpha_mcnks

def convert_wdt_to_adts(input_file, output_directory):
    # Read the contents of the provided old-style WDT file
    with open(input_file, 'rb') as f:
        file_content = f.read()

    # Parse the provided file content
    parsed_chunks = parse_chunks(file_content)

    # Determine the number of ADT files to create based on parsed data
    # For simplicity, assume one ADT file per MCNK chunk in WDT
    mcnk_chunks = [chunk for chunk in parsed_chunks if chunk.name == 'MCNK']
    adt_count = len(mcnk_chunks)

    # Create output directory if it doesn't exist
    os.makedirs(output_directory, exist_ok=True)

    # Convert each ADT and write to file
    for i in range(adt_count):
        adt_number = i
        adt_alpha = AdtAlpha(adt_number)
        adt_alpha.mhdr = next((chunk for chunk in parsed_chunks if chunk.name == 'MHDR'), None)
        adt_alpha.mcin = next((chunk for chunk in parsed_chunks if chunk.name == 'MCIN'), None)
        adt_alpha.mtex = next((chunk for chunk in parsed_chunks if chunk.name == 'MTEX'), None)
        adt_alpha.mddf = next((chunk for chunk in parsed_chunks if chunk.name == 'MDDF'), None)
        adt_alpha.modf = next((chunk for chunk in parsed_chunks if chunk.name == 'MODF'), None)
        adt_alpha.mcnksAlpha = [mcnk_chunks[i]]

        output_file = os.path.join(output_directory, f"output_{adt_number}.adt")
        adt_alpha.toFile(output_file)

        print(f"Converted {input_file} to {output_file} successfully.")

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Convert WDT file from old to new format.')
parser.add_argument('input_file', type=str, help='Path to the input old-style WDT file')
parser.add_argument('output_directory', type=str, help='Directory to output new-style ADT files')

args = parser.parse_args()

# Perform the conversion
convert_wdt_to_adts(args.input_file, args.output_directory)
