import os
import json
import sqlite3
import logging
import argparse
from chunk_decoders import chunk_decoders
from adt_chunk_decoders import parse_adt, adt_chunk_decoders
from common_helpers import ensure_folder_exists

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')

def read_chunks(file_path):
    with open(file_path, "rb") as f:
        file_size = os.path.getsize(file_path)
        data = f.read()

    offset = 0
    chunks = []
    while offset < file_size:
        chunk_id = data[offset:offset+4].decode('utf-8')
        chunk_size = int.from_bytes(data[offset+4:offset+8], byteorder='little')
        chunk_data = data[offset+8:offset+8+chunk_size]
        chunks.append({
            'id': chunk_id,
            'size': chunk_size,
            'data': chunk_data
        })
        logging.info(f"Read chunk: {chunk_id} (Size: {chunk_size})")
        offset += 8 + chunk_size

    return chunks

def create_database(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            file_name TEXT, 
            chunk_id TEXT, 
            chunk_size INTEGER, 
            chunk_data TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS parsed_chunks (
            file_name TEXT, 
            chunk_id TEXT, 
            chunk_size INTEGER, 
            chunk_data TEXT
        )
    """)
    conn.commit()
    return conn, cursor

def insert_data(cursor, file_name, chunks):
    for chunk in chunks:
        chunk_data_hex = chunk['data'].hex()
        cursor.execute("""
            INSERT INTO chunks (file_name, chunk_id, chunk_size, chunk_data) 
            VALUES (?, ?, ?, ?)
        """, (file_name, chunk['id'], chunk['size'], chunk_data_hex))
    logging.info(f"Inserted data for file {file_name}")

def insert_parsed_chunks(cursor, file_name, parsed_data):
    for chunk_id, chunk_data in parsed_data.items():
        json_data = json.dumps(chunk_data, default=lambda x: x.hex() if isinstance(x, bytes) else x)
        cursor.execute("""
            INSERT INTO parsed_chunks (file_name, chunk_id, chunk_size, chunk_data) 
            VALUES (?, ?, ?, ?)
        """, (file_name, chunk_id, len(json_data), json_data))
    logging.info(f"Inserted parsed chunks for file {file_name}")

def decode_chunks(data, chunk_decoders):
    detailed_chunks = {}

    for chunk in data:
        chunk_id = chunk['id']
        chunk_data = chunk['data']

        decoder = chunk_decoders.get(chunk_id) or chunk_decoders.get(reverse_chunk_id(chunk_id))
        if decoder:
            try:
                decoded_data = decoder(chunk_data)
                detailed_chunks[chunk_id] = decoded_data
            except Exception as e:
                logging.error(f"Error decoding chunk {chunk_id}: {e}")
                detailed_chunks[chunk_id] = {
                    "error": str(e),
                    "raw_data": chunk_data.hex()
                }
        else:
            logging.warning(f"No decoder for chunk: {chunk_id}")
            detailed_chunks[chunk_id] = {
                "raw_data": chunk_data.hex()
            }

    return detailed_chunks

def save_json(data, filepath):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def process_file(input_file, cursor, file_type, output_json):
    file_name = os.path.basename(input_file)
    if file_type == 'adt':
        parsed_data = parse_adt(input_file)
        insert_adt_data(cursor, file_name, parsed_data)
        detailed_data = decode_chunks(parsed_data, adt_chunk_decoders)
        insert_parsed_chunks(cursor, file_name, detailed_data)
    elif file_type in ['pm4', 'pd4']:
        chunks = read_chunks(input_file)
        insert_data(cursor, file_name, chunks)
        detailed_data = decode_chunks(chunks, chunk_decoders)
        insert_parsed_chunks(cursor, file_name, detailed_data)

    if output_json:
        initial_output = os.path.join(output_json, file_name.replace('.pm4', '_initial_analysis.json').replace('.adt', '_initial_analysis.json').replace('.pd4', '_initial_analysis.json'))
        detailed_output = os.path.join(output_json, file_name.replace('.pm4', '_detailed_analysis.json').replace('.adt', '_detailed_analysis.json').replace('.pd4', '_detailed_analysis.json'))
        
        save_json(parsed_data, initial_output)
        save_json(detailed_data, detailed_output)
        logging.info(f"Saved JSON analysis files for {file_name} at {output_json}")

def parse_adt(file_path):
    with open(file_path, 'rb') as file:
        data = file.read()
    
    offset = 0
    parsed_data = []

    while offset < len(data):
        chunk_id = data[offset:offset + 4].decode('utf-8')
        chunk_size, offset = decode_uint32(data, offset + 4)
        chunk_data = data[offset:offset + chunk_size]
        offset += chunk_size

        parsed_data.append({
            'id': chunk_id,
            'size': chunk_size,
            'data': chunk_data
        })

    return parsed_data

def reverse_chunk_id(chunk_id):
    return chunk_id[::-1]

def main():
    parser = argparse.ArgumentParser(description="Process PM4, PD4, and ADT files and store data in SQLite databases.")
    parser.add_argument("input_path", type=str, help="Path to the input file or directory.")
    parser.add_argument("output_dir", type=str, help="Path to the output directory.")
    parser.add_argument("--output_json", type=str, help="Path to the output directory for JSON analysis files.")
    args = parser.parse_args()

    ensure_folder_exists(args.output_dir)
    db_path = os.path.join(args.output_dir, 'chunk_data.db')
    conn, cursor = create_database(db_path)

    try:
        if os.path.isdir(args.input_path):
            for root, _, files in os.walk(args.input_path):
                for file in files:
                    if file.lower().endswith(('.pm4', '.pd4', '.adt')):
                        input_file = os.path.join(root, file)
                        file_type = file.split('.')[-1].lower()
                        try:
                            process_file(input_file, cursor, file_type, args.output_json)
                        except Exception as e:
                            logging.error(f"Failed to process file {input_file}: {e}")
        else:
            file_type = args.input_path.split('.')[-1].lower()
            try:
                process_file(args.input_path, cursor, file_type, args.output_json)
            except Exception as e:
                logging.error(f"Failed to process file {args.input_path}: {e}")

        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
