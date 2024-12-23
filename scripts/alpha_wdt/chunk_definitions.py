### Chunk Definitions: chunk_definitions.py
import os
import struct
import logging
from datetime import datetime

def parse_mver(data):
    version = struct.unpack('<I', data[:4])[0]
    logging.info(f"MVER Chunk: Version = {version}")

def parse_mphd(data):
    flags = struct.unpack('<I', data[:4])[0]
    logging.info(f"MPHD Chunk: Flags = {flags}")

def parse_main(data):
    entry_count = len(data) // 8
    logging.info(f"MAIN Chunk: Contains {entry_count} entries.")

    for i in range(entry_count):
        x, y = struct.unpack('<II', data[i*8:(i+1)*8])
        logging.info(f"Tile: X = {x}, Y = {y}")

def parse_mdnm(data):
    names = data.split(b'\x00')[:-1]
    logging.info(f"MDNM Chunk: {len(names)} file names.")
    for name in names:
        logging.info(f"File name: {name.decode('utf-8', 'ignore')}")

def parse_monm(data):
    names = data.split(b'\x00')[:-1]
    logging.info(f"MONM Chunk: {len(names)} file names.")
    for name in names:
        logging.info(f"File name: {name.decode('utf-8', 'ignore')}")

def parse_mcnk(data):
    if len(data) < 124:
        logging.warning(f"MCNK chunk is too small. Size = {len(data)}")
        return

    header = struct.unpack('<5I5I5I5I32x3f', data[:124])
    logging.info(f"MCNK Header: {header}")

def parse_mhdr(data):
    offsets = struct.unpack('<8I', data[:32])
    logging.info(f"MHDR Chunk: Offsets = {offsets}")

def parse_mcin(data):
    entry_count = len(data) // 16
    logging.info(f"MCIN Chunk: Contains {entry_count} entries.")
    for i in range(entry_count):
        entry = struct.unpack('<4I', data[i*16:(i+1)*16])
        logging.info(f"MCIN Entry {i}: {entry}")

def parse_mtex(data):
    textures = data.split(b'\x00')[:-1]
    logging.info(f"MTEX Chunk: Contains {len(textures)} textures.")
    for i, texture in enumerate(textures):
        logging.info(f"Texture {i}: {texture.decode('utf-8', 'ignore')}")

def parse_mddf(data):
    """
    Parses the MDDF chunk for doodad placement data.
    Decodes according to ADT/v18 specification with scale adjustment.
    """
    expected_entry_size = 36  # Fixed size for MDDF entries
    entry_count = len(data) // expected_entry_size

    logging.info(f"MDDF Chunk: Estimated {entry_count} entries (size {expected_entry_size} bytes each).")

    for i in range(entry_count):
        entry_data = data[i * expected_entry_size:(i + 1) * expected_entry_size]
        if len(entry_data) != expected_entry_size:
            logging.error(
                f"Corrupted MDDF entry {i}: Expected {expected_entry_size} bytes but got {len(entry_data)}. "
                f"Data: {entry_data.hex()}"
            )
            continue

        try:
            # Unpack the full entry
            mddf_id, unique_id = struct.unpack('<II', entry_data[:8])
            position = struct.unpack('<3f', entry_data[8:20])  # X, Y, Z
            rotation = struct.unpack('<3f', entry_data[20:32])  # Roll, Pitch, Yaw
            scale_raw, flags = struct.unpack('<HH', entry_data[32:36])

            # Convert scale to a float
            scale = scale_raw / 1024.0

            # Log the parsed entry
            logging.info(
                f"MDDF Entry {i}: ID: {mddf_id}, UniqueID: {unique_id}, "
                f"Position: ({position[0]:.2f}, {position[1]:.2f}, {position[2]:.2f}), "
                f"Rotation: ({rotation[0]:.2f}, {rotation[1]:.2f}, {rotation[2]:.2f}), "
                f"Scale: {scale:.2f}, Flags: {flags}"
            )
        except struct.error as e:
            logging.error(
                f"Error unpacking MDDF entry {i}: {e}. Data: {entry_data.hex()}"
            )

def parse_modf(data):
    entry_count = len(data) // 64
    logging.info(f"MODF Chunk: Contains {entry_count} entries.")
    for i in range(entry_count):
        entry = struct.unpack('<2I3f3f6f4H', data[i*64:(i+1)*64])
        logging.info(f"MODF Entry {i}: {entry}")
