# main_parser.py

import os
import json
import sqlite3
import logging
import argparse
from chunk_decoders import chunk_decoders
from adt_chunk_decoders import adt_chunk_decoders, parse_adt
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
            'data': list(chunk_data)
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
    conn.commit()
    return conn, cursor

def insert_data(cursor, file_name, chunks):
    for chunk in chunks:
        cursor.execute("""
            INSERT INTO chunks (file_name, chunk_id, chunk_size, chunk_data) 
            VALUES (?, ?, ?, ?)
        """, (file_name, chunk['id'], chunk['size'], json.dumps(chunk['data'])))
    logging.info(f"Inserted data for file {file_name}")

def process_file(input_file, cursor, file_type):
    if file_type == 'adt':
        parsed_data = parse_adt(input_file)
        insert_adt_data(cursor, os.path.basename(input_file), parsed_data)
    elif file_type in ['pm4', 'pd4']:
        chunks = read_chunks(input_file)
        insert_data(cursor, os.path.basename(input_file), chunks)

def insert_adt_data(cursor, file_name, parsed_data):
    for chunk_id, chunk_data in parsed_data.items():
        cursor.execute("""
            INSERT INTO chunks (file_name, chunk_id, chunk_size, chunk_data) 
            VALUES (?, ?, ?, ?)
        """, (file_name, chunk_id, len(chunk_data), json.dumps(chunk_data)))
    logging.info(f"Inserted ADT data for file {file_name}")

def main():
    parser = argparse.ArgumentParser(description="Process PM4, PD4, and ADT files and store data in SQLite databases.")
    parser.add_argument("input_path", type=str, help="Path to the input file or directory.")
    parser.add_argument("output_dir", type=str, help="Path to the output directory.")
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
                            process_file(input_file, cursor, file_type)
                        except Exception as e:
                            logging.error(f"Failed to process file {input_file}: {e}")
        else:
            file_type = args.input_path.split('.')[-1].lower()
            try:
                process_file(args.input_path, cursor, file_type)
            except Exception as e:
                logging.error(f"Failed to process file {args.input_path}: {e}")

        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
