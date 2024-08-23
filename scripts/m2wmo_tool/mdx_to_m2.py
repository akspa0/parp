import struct

class MDXtoM2Converter:
    def __init__(self, filepath):
        self.filepath = filepath
        self.magic = None
        self.version = None
        self.chunks = []
        self.m2_data = b''

    def read(self):
        with open(self.filepath, 'rb') as f:
            self.magic = f.read(4).decode()
            self.version = struct.unpack('I', f.read(4))[0]
            while True:
                chunk_header = f.read(8)
                if not chunk_header:
                    break
                chunk_id, chunk_size = struct.unpack('4sI', chunk_header)
                chunk_data = f.read(chunk_size)
                self.chunks.append((chunk_id, chunk_size, chunk_data))
                if len(chunk_data) < chunk_size:
                    break

    def parse_chunks(self):
        self.vertices = []
        self.normals = []
        self.textures = []
        self.sequences = []
        self.animations = []

        for chunk_id, chunk_size, chunk_data in self.chunks:
            if chunk_id == b'MODL':
                self.parse_modl_chunk(chunk_data)
            elif chunk_id == b'VRTX':
                self.parse_vertex_chunk(chunk_data)
            elif chunk_id == b'NRMS':
                self.parse_normal_chunk(chunk_data)
            elif chunk_id == b'TEXS':
                self.parse_texture_chunk(chunk_data)
            elif chunk_id == b'SEQS':
                self.parse_sequence_chunk(chunk_data)
            elif chunk_id == b'PIVT':
                self.parse_pivot_chunk(chunk_data)
            elif chunk_id in [b'KMAT', b'KGAO', b'KGAC', b'KGSC', b'KGT', b'KGRS']:
                self.parse_animation_chunk(chunk_id, chunk_data)
            # Add other chunk handlers here

    def parse_modl_chunk(self, data):
        self.model_name = data[:80].decode().rstrip('\0')
        self.global_properties = struct.unpack('3f3fI', data[80:])

    def parse_vertex_chunk(self, data):
        vertex_size = 36
        num_vertices = len(data) // vertex_size
        self.vertices = []
        for i in range(num_vertices):
            offset = i * vertex_size
            vertex = struct.unpack_from('fffBBBBfff', data, offset)
            self.vertices.append(vertex)

    def parse_normal_chunk(self, data):
        normal_size = 12
        num_normals = len(data) // normal_size
        self.normals = []
        for i in range(num_normals):
            offset = i * normal_size
            normal = struct.unpack_from('fff', data, offset)
            self.normals.append(normal)

    def parse_texture_chunk(self, data):
        num_textures = len(data) // 268
        self.textures = []
        for i in range(num_textures):
            offset = i * 268
            texture = struct.unpack_from('I260sII', data, offset)
            self.textures.append(texture)

    def parse_sequence_chunk(self, data):
        num_sequences = len(data) // 132
        self.sequences = []
        for i in range(num_sequences):
            offset = i * 132
            sequence = struct.unpack_from('80s2IIfI', data, offset)
            self.sequences.append(sequence)

    def parse_pivot_chunk(self, data):
        num_pivots = len(data) // 12
        self.pivots = []
        for i in range(num_pivots):
            offset = i * 12
            pivot = struct.unpack_from('fff', data, offset)
            self.pivots.append(pivot)

    def parse_animation_chunk(self, chunk_id, data):
        num_keys, key_type, global_seq_id = struct.unpack_from('3I', data, 8)
        keys = []
        offset = 20
        for _ in range(num_keys):
            if key_type == 0x1:  # LINEAR
                time, value = struct.unpack_from('If', data, offset)
                keys.append((time, value))
                offset += 8
            elif key_type in [0x2, 0x3]:  # HERMITE, BEZIER
                time, value, in_tan, out_tan = struct.unpack_from('Ifff', data, offset)
                keys.append((time, value, in_tan, out_tan))
                offset += 16
        self.animations.append((chunk_id, key_type, global_seq_id, keys))

    def convert_to_m2(self):
        self.m2_data = b''
        self.m2_data += struct.pack('4s', b'MD20')
        self.m2_data += struct.pack('I', 0)  # Placeholder for file size
        self.m2_data += struct.pack('I', 0)  # Placeholder for number of chunks
        self.m2_data += struct.pack('I', self.version)

        chunk_data = b''
        for chunk_id, chunk_size, chunk_data in self.chunks:
            if chunk_id == b'MODL':
                chunk_data += struct.pack('4sI', b'MODL', len(chunk_data))
                chunk_data += chunk_data
            elif chunk_id == b'VRTX':
                chunk_data += struct.pack('4sI', b'VRTX', len(chunk_data))
                chunk_data += chunk_data
            elif chunk_id == b'NRMS':
                chunk_data += struct.pack('4sI', b'NRMS', len(chunk_data))
                chunk_data += chunk_data
            elif chunk_id == b'TEXS':
                chunk_data += struct.pack('4sI', b'TEXS', len(chunk_data))
                chunk_data += chunk_data
            elif chunk_id == b'SEQS':
                chunk_data += struct.pack('4sI', b'SEQS', len(chunk_data))
                chunk_data += chunk_data
            elif chunk_id == b'PIVT':
                chunk_data += struct.pack('4sI', b'PIVT', len(chunk_data))
                chunk_data += chunk_data
            elif chunk_id in [b'KMAT', b'KGAO', b'KGAC', b'KGSC', b'KGT', b'KGRS']:
                chunk_data += struct.pack('4sI', chunk_id, len(chunk_data))
                chunk_data += chunk_data
            # Handle other chunks similarly

        file_size = len(chunk_data) + 16
        num_chunks = len(self.chunks)
        self.m2_data = self.m2_data[:4] + struct.pack('I', file_size) + struct.pack('I', num_chunks) + self.m2_data[12:] + chunk_data

    def save_m2(self, filepath):
        with open(filepath, 'wb') as f:
            f.write(self.m2_data)
