import os
import json
import sqlite3
import logging
import argparse
from collections import defaultdict
from chunk_decoders import chunk_decoders
from adt_chunk_decoders import parse_adt, adt_chunk_decoders
from common_helpers import ensure_folder_exists
import struct

# Setup logging
log_file = 'processing.log'
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s', handlers=[
    logging.FileHandler(log_file),
    logging.StreamHandler()
])

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
    ensure_folder_exists(os.path.dirname(db_path))
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunk_fields (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT, 
                chunk_id TEXT, 
                record_index INTEGER,
                field_name TEXT,
                field_value TEXT,
                field_type TEXT
            )
        """)
        conn.commit()
        return conn, cursor
    except sqlite3.OperationalError as e:
        logging.error(f"Unable to open database file: {db_path}. Error: {e}")
        raise

def insert_chunk_field(cursor, file_name, chunk_id, record_index, field_name, field_value, field_type):
    cursor.execute("""
        INSERT INTO chunk_fields (file_name, chunk_id, record_index, field_name, field_value, field_type) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, (file_name, chunk_id, record_index, field_name, json.dumps(field_value, default=lambda x: x.hex() if isinstance(x, bytes) else x), field_type))
    logging.info(f"Inserted field {field_name} of type {field_type} for record {record_index} in chunk {chunk_id} in file {file_name}")

def decode_chunks(data, chunk_decoders):
    detailed_chunks = []

    for chunk in data:
        chunk_id = chunk['id']
        chunk_data = chunk['data']

        decoder = chunk_decoders.get(chunk_id) or chunk_decoders.get(reverse_chunk_id(chunk_id))
        if decoder:
            try:
                decoded_data = decoder(chunk_data)
                detailed_chunks.append({
                    "id": chunk_id,
                    "data": decoded_data
                })
            except struct.error as e:
                logging.error(f"Error decoding chunk {chunk_id}: {e}")
                detailed_chunks.append({
                    "id": chunk_id,
                    "data": {
                        "error": str(e),
                        "raw_data": chunk_data.hex()
                    }
                })
        else:
            logging.warning(f"No decoder for chunk: {chunk_id}")
            detailed_chunks.append({
                "id": chunk_id,
                "data": {
                    "raw_data": chunk_data.hex()
                }
            })

    return detailed_chunks

def save_json(data, filepath):
    ensure_folder_exists(os.path.dirname(filepath))
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def analyze_data_type(value):
    if isinstance(value, dict):
        return "dict"
    elif isinstance(value, list):
        return "list"
    elif isinstance(value, int):
        return "int"
    elif isinstance(value, float):
        return "float"
    elif isinstance(value, str):
        return "str"
    else:
        return "unknown"

def process_file(input_file, cursor, file_type, output_json):
    file_name = os.path.basename(input_file)
    parsed_data = []
    detailed_data = []

    if file_type == 'adt':
        parsed_data = parse_adt(input_file)
        detailed_data = decode_chunks(parsed_data, adt_chunk_decoders)
    elif file_type in ['pm4', 'pd4']:
        chunks = read_chunks(input_file)
        detailed_data = decode_chunks(chunks, chunk_decoders)

    # Insert parsed chunks into the database
    record_index = 0
    for chunk in detailed_data:
        for record in chunk['data']:
            if isinstance(record, dict):
                for field_name, field_value in record.items():
                    field_type = analyze_data_type(field_value)
                    insert_chunk_field(cursor, file_name, chunk['id'], record_index, field_name, field_value, field_type)
            elif isinstance(record, list):
                for i, value in enumerate(record):
                    field_type = analyze_data_type(value)
                    insert_chunk_field(cursor, file_name, chunk['id'], record_index, f"list_item_{i}", value, field_type)
            elif isinstance(record, (int, float, str)):
                field_type = analyze_data_type(record)
                field_name = f"{type(record).__name__}_value"
                insert_chunk_field(cursor, file_name, chunk['id'], record_index, field_name, record, field_type)
            else:
                logging.error(f"Expected a dictionary or list for chunk record in chunk {chunk['id']} at record {record_index}, got {type(record)}: {record}")
                insert_chunk_field(cursor, file_name, chunk['id'], record_index, "unknown", str(record), "unknown")
            record_index += 1

    if output_json:
        initial_output = os.path.join(output_json, file_name.replace('.pm4', '_initial_analysis.json').replace('.adt', '_initial_analysis.json').replace('.pd4', '_initial_analysis.json'))
        detailed_output = os.path.join(output_json, file_name.replace('.pm4', '_detailed_analysis.json').replace('.adt', '_detailed_analysis.json').replace('.pd4', '_detailed_analysis.json'))
        
        save_json(parsed_data, initial_output)
        save_json(detailed_data, detailed_output)
        logging.info(f"Saved JSON analysis files for {file_name} at {output_json}")

def export_to_json(db_path, output_dir):
    ensure_folder_exists(output_dir)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = "SELECT file_name, chunk_id, record_index, field_name, field_value, field_type FROM chunk_fields"
    cursor.execute(query)
    rows = cursor.fetchall()

    data = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    for row in rows:
        file_name, chunk_id, record_index, field_name, field_value, field_type = row
        data[file_name][chunk_id][record_index][field_name] = {
            "value": json.loads(field_value),
            "type": field_type
        }

    for file_name, chunks in data.items():
        output_file = os.path.join(output_dir, f"{file_name}_exported.json")
        save_json(chunks, output_file)
        logging.info(f"Exported data to {output_file}")

    conn.close()

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
    parser = argparse.ArgumentParser(description="Process PM4, PD4, and ADT files, store data in SQLite databases, and optionally export to JSON.")
    parser.add_argument("input_path", type=str, help="Path to the input file or directory.")
    parser.add_argument("output_dir", type=str, help="Path to the output directory.")
    parser.add_argument("--output_json", type=str, help="Directory to save JSON analysis files.")
    parser.add_argument("--export_json", type=str, help="Directory to export data from the database to JSON files.")
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

    if args.export_json:
        export_to_json(db_path, args.export_json)

if __name__ == "__main__":
    main()
