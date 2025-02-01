import struct
import logging


def parse_mcly(data):
    """
    Parses the MCLY chunk for layer information.
    Each entry is 16 bytes.
    """
    entry_size = 16
    entry_count = len(data) // entry_size
    logging.info(f"MCLY Chunk: Contains {entry_count} entries.")
    for i in range(entry_count):
        try:
            texture_id, flags, offset, effect_id = struct.unpack('<IIBxH', data[i * entry_size:(i + 1) * entry_size])
            logging.info(f"Layer {i}: TextureID={texture_id}, Flags={flags:#010x}, Offset={offset}, EffectID={effect_id}")
        except struct.error as e:
            logging.error(f"Error unpacking MCLY entry {i}: {e}")


def parse_mcvt(data):
    """
    Parses the MCVT chunk for heightmap data.
    Logs the first few height values for sanity check.
    """
    entry_count = len(data) // 4
    logging.info(f"MCVT Chunk: Contains {entry_count} height values.")
    for i in range(min(entry_count, 10)):  # Log only the first 10 entries
        try:
            height = struct.unpack('<f', data[i * 4:(i + 1) * 4])[0]
            logging.info(f"Height {i}: {height:.2f}")
        except struct.error as e:
            logging.error(f"Error unpacking MCVT entry {i}: {e}")


def parse_mcnr(data):
    """
    Parses the MCNR chunk for normal data.
    Each normal is 3 floats (12 bytes).
    """
    entry_size = 12
    entry_count = len(data) // entry_size
    logging.info(f"MCNR Chunk: Contains {entry_count} normals.")
    for i in range(min(entry_count, 10)):  # Log only the first 10 entries
        try:
            normal = struct.unpack('<3f', data[i * entry_size:(i + 1) * entry_size])
            logging.info(f"Normal {i}: X={normal[0]:.2f}, Y={normal[1]:.2f}, Z={normal[2]:.2f}")
        except struct.error as e:
            logging.error(f"Error unpacking MCNR entry {i}: {e}")


def parse_mccv(data):
    """
    Parses the MCCV chunk for vertex color data.
    Each vertex color is 4 bytes (RGBA).
    """
    entry_size = 4
    entry_count = len(data) // entry_size
    logging.info(f"MCCV Chunk: Contains {entry_count} vertex colors.")
    for i in range(min(entry_count, 10)):  # Log only the first 10 entries
        try:
            r, g, b, a = struct.unpack('<4B', data[i * entry_size:(i + 1) * entry_size])
            logging.info(f"Vertex Color {i}: R={r}, G={g}, B={b}, A={a}")
        except struct.error as e:
            logging.error(f"Error unpacking MCCV entry {i}: {e}")


def parse_mcrf(data):
    """
    Parses the MCRF chunk for references.
    """
    entry_size = 4
    entry_count = len(data) // entry_size
    logging.info(f"MCRF Chunk: Contains {entry_count} references.")
    for i in range(entry_count):
        try:
            reference = struct.unpack('<I', data[i * entry_size:(i + 1) * entry_size])[0]
            logging.info(f"Reference {i}: {reference}")
        except struct.error as e:
            logging.error(f"Error unpacking MCRF entry {i}: {e}")


def parse_mcsh(data):
    """
    Parses the MCSH chunk for shadow map data.
    """
    logging.info(f"MCSH Chunk: Contains {len(data)} bytes of shadow data.")
    # Shadow data format is currently unclear; log the size and first few bytes
    logging.info(f"Shadow Data (first 16 bytes): {data[:16].hex()}")


def parse_mcal(data):
    """
    Parses the MCAL chunk for alpha maps.
    """
    logging.info(f"MCAL Chunk: Contains {len(data)} bytes of alpha map data.")
    # Alpha map format varies; log the size and first few bytes
    logging.info(f"Alpha Map Data (first 16 bytes): {data[:16].hex()}")


def parse_mcnk_additional(chunk_name, chunk_data):
    """
    Directs parsing for additional MCNK sub-chunks like MCLY, MCVT, etc.
    """
    if chunk_name == 'MCLY':
        parse_mcly(chunk_data)
    elif chunk_name == 'MCVT':
        parse_mcvt(chunk_data)
    elif chunk_name == 'MCNR':
        parse_mcnr(chunk_data)
    elif chunk_name == 'MCCV':
        parse_mccv(chunk_data)
    elif chunk_name == 'MCRF':
        parse_mcrf(chunk_data)
    elif chunk_name == 'MCSH':
        parse_mcsh(chunk_data)
    elif chunk_name == 'MCAL':
        parse_mcal(chunk_data)
    else:
        logging.warning(f"Unhandled MCNK sub-chunk: {chunk_name}")
