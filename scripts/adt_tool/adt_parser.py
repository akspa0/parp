import struct
import json

class ADTParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.file_data = None
        self.parsed_data = {}

    def read_file(self):
        with open(self.file_path, 'rb') as file:
            self.file_data = file.read()

    def parse_chunk(self, offset, length, fmt):
        return struct.unpack(fmt, self.file_data[offset:offset + length])

    def parse_header(self):
        offset = 0
        self.parsed_data['MVER'], = self.parse_chunk(offset, 4, 'I')
        offset += 4

        mhdr_offset = struct.unpack('I', self.file_data[offset:offset + 4])[0]
        self.parsed_data['MHDR'] = {
            'ofsMCIN': struct.unpack('I', self.file_data[mhdr_offset:mhdr_offset + 4])[0],
            'ofsMTEX': struct.unpack('I', self.file_data[mhdr_offset + 4:mhdr_offset + 8])[0],
            'ofsMMDX': struct.unpack('I', self.file_data[mhdr_offset + 8:mhdr_offset + 12])[0],
            'ofsMMID': struct.unpack('I', self.file_data[mhdr_offset + 12:mhdr_offset + 16])[0],
            'ofsMWMO': struct.unpack('I', self.file_data[mhdr_offset + 16:mhdr_offset + 20])[0],
            'ofsMWID': struct.unpack('I', self.file_data[mhdr_offset + 20:mhdr_offset + 24])[0],
            'ofsMDDF': struct.unpack('I', self.file_data[mhdr_offset + 24:mhdr_offset + 28])[0],
            'ofsMODF': struct.unpack('I', self.file_data[mhdr_offset + 28:mhdr_offset + 32])[0],
            'ofsMH2O': struct.unpack('I', self.file_data[mhdr_offset + 32:mhdr_offset + 36])[0],
            'ofsMFBO': struct.unpack('I', self.file_data[mhdr_offset + 36:mhdr_offset + 40])[0],
            'ofsMTFX': struct.unpack('I', self.file_data[mhdr_offset + 40:mhdr_offset + 44])[0]
        }

    def parse_mcin(self, offset):
        entry_fmt = '4I'
        entry_size = struct.calcsize(entry_fmt)
        entries = []
        for i in range(256):
            entry = self.parse_chunk(offset + i * entry_size, entry_size, entry_fmt)
            entries.append({
                'offset': entry[0],
                'size': entry[1],
                'flags': entry[2],
                'asyncID': entry[3]
            })
        return entries

    def parse_mtex(self, offset):
        texture_files = []
        while True:
            end = self.file_data.find(b'\x00', offset)
            if end == -1:
                break
            texture_files.append(self.file_data[offset:end].decode('utf-8'))
            offset = end + 1
        return texture_files

    def parse_mmdx(self, offset):
        model_files = []
        while True:
            end = self.file_data.find(b'\x00', offset)
            if end == -1:
                break
            model_files.append(self.file_data[offset:end].decode('utf-8'))
            offset = end + 1
        return model_files

    def parse_mmid(self, offset, num_entries):
        entry_fmt = 'I'
        entry_size = struct.calcsize(entry_fmt)
        entries = []
        for i in range(num_entries):
            entry = self.parse_chunk(offset + i * entry_size, entry_size, entry_fmt)
            entries.append({
                'offset': entry[0]
            })
        return entries

    def parse_mwmo(self, offset):
        object_files = []
        while True:
            end = self.file_data.find(b'\x00', offset)
            if end == -1:
                break
            object_files.append(self.file_data[offset:end].decode('utf-8'))
            offset = end + 1
        return object_files

    def parse_mwid(self, offset, num_entries):
        entry_fmt = 'I'
        entry_size = struct.calcsize(entry_fmt)
        entries = []
        for i in range(num_entries):
            entry = self.parse_chunk(offset + i * entry_size, entry_size, entry_fmt)
            entries.append({
                'offset': entry[0]
            })
        return entries

    def parse_mddf(self, offset, num_entries):
        entry_fmt = '3I3f3H2I'
        entry_size = struct.calcsize(entry_fmt)
        entries = []
        for i in range(num_entries):
            entry = self.parse_chunk(offset + i * entry_size, entry_size, entry_fmt)
            entries.append({
                'mmidEntry': entry[0],
                'uniqueID': entry[1],
                'position': {
                    'x': entry[2],
                    'y': entry[3],
                    'z': entry[4]
                },
                'rotation': {
                    'x': entry[5],
                    'y': entry[6],
                    'z': entry[7]
                },
                'scale': entry[8],
                'flags': entry[9]
            })
        return entries

    def parse_modf(self, offset, num_entries):
        entry_fmt = '3I3f3f3fI'
        entry_size = struct.calcsize(entry_fmt)
        entries = []
        for i in range(num_entries):
            entry = self.parse_chunk(offset + i * entry_size, entry_size, entry_fmt)
            entries.append({
                'mwidEntry': entry[0],
                'uniqueID': entry[1],
                'position': {
                    'x': entry[2],
                    'y': entry[3],
                    'z': entry[4]
                },
                'rotation': {
                    'x': entry[5],
                    'y': entry[6],
                    'z': entry[7]
                },
                'lowerBounds': {
                    'x': entry[8],
                    'y': entry[9],
                    'z': entry[10]
                },
                'upperBounds': {
                    'x': entry[11],
                    'y': entry[12],
                    'z': entry[13]
                },
                'flags': entry[14]
            })
        return entries

    def parse_mh2o(self, offset):
        # Parsing logic for MH2O chunk
        header_fmt = 'I3f2I'
        header_size = struct.calcsize(header_fmt)
        headers = []
        while offset < len(self.file_data):
            header = self.parse_chunk(offset, header_size, header_fmt)
            headers.append({
                'flags': header[0],
                'height1': header[1],
                'height2': header[2],
                'xOffset': header[3],
                'yOffset': header[4],
                'layerCount': header[5],
                'vertexCount': header[6]
            })
            offset += header_size

        entries = []
        for header in headers:
            layer_fmt = 'I2f'
            layer_size = struct.calcsize(layer_fmt)
            layers = []
            for _ in range(header['layerCount']):
                layer = self.parse_chunk(offset, layer_size, layer_fmt)
                layers.append({
                    'height': layer[0],
                    'depth': layer[1],
                    'waterType': layer[2]
                })
                offset += layer_size
            entries.append({'header': header, 'layers': layers})
        return entries

    def parse_mfbo(self, offset):
        # Parsing logic for MFBO chunk
        entry_fmt = 'I2f3I'
        entry_size = struct.calcsize(entry_fmt)
        entries = []
        while offset < len(self.file_data):
            entry = self.parse_chunk(offset, entry_size, entry_fmt)
            entries.append({
                'fogOffset': entry[0],
                'fogSize': entry[1],
                'density': entry[2],
                'minFog': entry[3],
                'maxFog': entry[4],
                'color': entry[5]
            })
            offset += entry_size
        return entries

    def parse_mtfx(self, offset):
        # Parsing logic for MTFX chunk
        entry_fmt = 'I3fI'
        entry_size = struct.calcsize(entry_fmt)
        entries = []
        while offset < len(self.file_data):
            entry = self.parse_chunk(offset, entry_size, entry_fmt)
            entries.append({
                'effectID': entry[0],
                'posX': entry[1],
                'posY': entry[2],
                'posZ': entry[3],
                'rotation': entry[4]
            })
            offset += entry_size
        return entries

    def parse_chunks(self):
        mhdr = self.parsed_data['MHDR']
        self.parsed_data['MCIN'] = self.parse_mcin(mhdr['ofsMCIN'])
        self.parsed_data['MTEX'] = self.parse_mtex(mhdr['ofsMTEX'])
        self.parsed_data['MMDX'] = self.parse_mmdx(mhdr['ofsMMDX'])
        self.parsed_data['MMID'] = self.parse_mmid(mhdr['ofsMMID'], len(self.parsed_data['MMDX']))
        self.parsed_data['MWMO'] = self.parse_mwmo(mhdr['ofsMWMO'])
        self.parsed_data['MWID'] = self.parse_mwid(mhdr['ofsMWID'], len(self.parsed_data['MWMO']))
        self.parsed_data['MDDF'] = self.parse_mddf(mhdr['ofsMDDF'], len(self.parsed_data['MMID']))
        self.parsed_data['MODF'] = self.parse_modf(mhdr['ofsMODF'], len(self.parsed_data['MWID']))
        self.parsed_data['MH2O'] = self.parse_mh2o(mhdr['ofsMH2O'])
        self.parsed_data['MFBO'] = self.parse_mfbo(mhdr['ofsMFBO'])
        self.parsed_data['MTFX'] = self.parse_mtfx(mhdr['ofsMTFX'])

    def parse(self):
        self.read_file()
        self.parse_header()
        self.parse_chunks()

    def to_json(self):
        return json.dumps(self.parsed_data, indent=4)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Parse an ADT file and output its structure as JSON.")
    parser.add_argument("file_path", help="Path to the ADT file to be parsed")

    args = parser.parse_args()
    adt_parser = ADTParser(args.file_path)
    adt_parser.parse()
    adt_json_data = adt_parser.to_json()
    print(adt_json_data)
