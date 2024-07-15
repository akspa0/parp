import struct
import logging

def reverse_chunk_id(chunk_id):
    return chunk_id[::-1]

def parse_vertices(chunk):
    count = len(chunk['data']) // 12
    vertices = struct.unpack_from('<' + 'fff' * count, chunk['data'])
    return [{"x": vertices[i], "y": vertices[i + 1], "z": vertices[i + 2]} for i in range(0, len(vertices), 3)]

def parse_indices(chunk):
    count = len(chunk['data']) // 2
    indices = struct.unpack_from('<' + 'H' * count, chunk['data'])
    return list(indices)

def parse_normals(chunk):
    count = len(chunk['data']) // 12
    normals = struct.unpack_from('<' + 'fff' * count, chunk['data'])
    return [{"nx": normals[i], "ny": normals[i + 1], "nz": normals[i + 2]} for i in range(0, len(normals), 3)]

def extract_wmo_root_data(chunks):
    vertices = []
    faces = []
    normals = []
    
    for chunk in chunks:
        chunk_id = chunk['id']
        reverse_id = reverse_chunk_id(chunk_id)
        logging.info(f"Analyzing chunk: {chunk_id} (or {reverse_id})")
        if chunk_id in ['MOVT', 'MOVI', 'MONR'] or reverse_id in ['MOVT', 'MOVI', 'MONR']:
            if chunk_id == 'MOVT' or reverse_id == 'MOVT':
                vertices = parse_vertices(chunk)
            elif chunk_id == 'MOVI' or reverse_id == 'MOVI':
                faces = parse_indices(chunk)
            elif chunk_id == 'MONR' or reverse_id == 'MONR':
                normals = parse_normals(chunk)
        else:
            logging.info(f"Chunk {chunk_id} is not identified for vertices, faces, or normals")

    return {
        "vertices": vertices,
        "faces": faces,
        "normals": normals
    }

def extract_wmo_group_data(chunks):
    vertices = []
    faces = []
    normals = []
    
    for chunk in chunks:
        chunk_id = chunk['id']
        reverse_id = reverse_chunk_id(chunk_id)
        logging.info(f"Analyzing chunk: {chunk_id} (or {reverse_id})")
        if chunk_id == 'MOGP' or reverse_id == 'MOGP':
            sub_chunks = read_chunks_from_data(chunk['data'])
            for sub_chunk in sub_chunks:
                sub_chunk_id = sub_chunk['id']
                sub_reverse_id = reverse_chunk_id(sub_chunk_id)
                if sub_chunk_id in ['MOVT', 'MOVI', 'MONR'] or sub_reverse_id in ['MOVT', 'MOVI', 'MONR']:
                    if sub_chunk_id == 'MOVT' or sub_reverse_id == 'MOVT':
                        vertices = parse_vertices(sub_chunk)
                    elif sub_chunk_id == 'MOVI' or sub_reverse_id == 'MOVI':
                        faces = parse_indices(sub_chunk)
                    elif sub_chunk_id == 'MONR' or sub_reverse_id == 'MONR':
                        normals = parse_normals(sub_chunk)
        else:
            logging.info(f"Chunk {chunk_id} is not identified for vertices, faces, or normals")

    return {
        "vertices": vertices,
        "faces": faces,
        "normals": normals
}

def read_chunks_from_data(data):
    offset = 0
    data_size = len(data)
    chunks = []
    while offset < data_size:
        chunk_id = data[offset:offset+4]
        try:
            chunk_id_str = chunk_id.decode('utf-8')
        except UnicodeDecodeError:
            logging.error(f"Failed to decode chunk ID at offset {offset}. Skipping this chunk.")
            offset += 4
            continue
        
        chunk_size = int.from_bytes(data[offset+4:offset+8], byteorder='little')
        chunk_data = data[offset+8:offset+8+chunk_size]
        chunks.append({
            'id': chunk_id_str,
            'size': chunk_size,
            'data': chunk_data
        })
        offset += 8 + chunk_size
    return chunks
