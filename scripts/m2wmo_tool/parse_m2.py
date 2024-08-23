import struct

def read_m2(filepath):
    with open(filepath, 'rb') as f:
        magic = f.read(4).decode()
        version = struct.unpack('I', f.read(4))[0]
        chunks = []
        while True:
            chunk_header = f.read(8)
            if not chunk_header:
                break
            chunk_id, chunk_size = struct.unpack('4sI', chunk_header)
            chunk_data = f.read(chunk_size)
            chunks.append((chunk_id, chunk_size, chunk_data))
            if len(chunk_data) < chunk_size:
                break
    return magic, version, chunks

# Path to the provided M2 file
m2_filepath = 'in-0.11/xyz.m2'

# Read and print the M2 file details
m2_magic, m2_version, m2_chunks = read_m2(m2_filepath)
print((m2_magic, m2_version))
for chunk in m2_chunks[:5]:  # Print first 5 chunks for brevity
    print(chunk)
