# pm4-tool_0x07.py

import os
import json
import sqlite3
import logging
import argparse
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from chunk_decoders import chunk_decoders
from adt_chunk_decoders import parse_adt, adt_chunk_decoders
from common_helpers import ensure_folder_exists
import struct

# Setup logging with a timestamped log file
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = f'processing_{timestamp}.log'
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

def convert_to_json(value):
    if isinstance(value, dict) or isinstance(value, list):
        return json.dumps(value)
    return value

def insert_chunk_field_batch(cursor, batch):
    batch = [(file_name, chunk_id, record_index, field_name, convert_to_json(field_value), field_type) for file_name, chunk_id, record_index, field_name, field_value, field_type in batch]
    cursor.executemany("""
        INSERT INTO chunk_fields (file_name, chunk_id, record_index, field_name, field_value, field_type) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, batch)
    logging.info(f"Inserted {len(batch)} records in batch")

def decode_chunks(data, chunk_decoders):
    detailed_chunks = []

    for chunk in data:
        chunk_id = chunk['id']
        chunk_data = chunk['data']

        decoder = chunk_decoders.get(chunk_id) or chunk_decoders.get(reverse_chunk_id(chunk_id))
        if decoder:
            try:
                decoded_data = decoder(chunk_data)
                if isinstance(decoded_data, list):
                    for i, entry in enumerate(decoded_data):
                        detailed_chunks.append({
                            "id": chunk_id,
                            "index": i,
                            "data": entry
                        })
                else:
                    detailed_chunks.append({
                        "id": chunk_id,
                        "index": 0,
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

def detect_data_type(data):
    try:
        json.loads(data)
        return 'json'
    except (ValueError, TypeError):
        pass

    try:
        int(data)
        return 'int'
    except ValueError:
        pass

    try:
        float(data)
        return 'float'
    except ValueError:
        pass

    if isinstance(data, bytes):
        return 'bytes'

    return 'str'

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

def process_file(input_file, output_dir, output_json):
    file_name = os.path.basename(input_file)
    db_path = os.path.join(output_dir, f'{os.path.splitext(file_name)[0]}.db')
    conn, cursor = create_database(db_path)
    parsed_data = []
    detailed_data = []

    try:
        if file_name.lower().endswith('adt'):
            parsed_data = parse_adt(input_file)
            detailed_data = decode_chunks(parsed_data, adt_chunk_decoders)
        elif file_name.lower().endswith(('pm4', 'pd4')):
            chunks = read_chunks(input_file)
            detailed_data = decode_chunks(chunks, chunk_decoders)

        # Insert parsed chunks into the database in batches
        batch = []
        record_index = 0
        for chunk in detailed_data:
            chunk_id = chunk['id']
            chunk_data = chunk['data']
            if isinstance(chunk_data, dict):
                for field_name, field_value in chunk_data.items():
                    field_type = analyze_data_type(field_value)
                    batch.append((file_name, chunk_id, record_index, field_name, field_value, field_type))
            elif isinstance(chunk_data, list):
                for i, value in enumerate(chunk_data):
                    field_type = analyze_data_type(value)
                    batch.append((file_name, chunk_id, record_index, f"list_item_{i}", value, field_type))
            elif isinstance(chunk_data, (int, float, str)):
                field_type = analyze_data_type(chunk_data)
                field_name = f"{type(chunk_data).__name__}_value"
                batch.append((file_name, chunk_id, record_index, field_name, chunk_data, field_type))
            else:
                logging.error(f"Expected a dictionary or list for chunk data in chunk {chunk_id} at record {record_index}, got {type(chunk_data)}: {chunk_data}")
                batch.append((file_name, chunk_id, record_index, "unknown", str(chunk_data), "unknown"))

            if len(batch) >= 1000:  # Batch size limit
                insert_chunk_field_batch(cursor, batch)
                conn.commit()
                batch = []

            record_index += 1

        if batch:
            insert_chunk_field_batch(cursor, batch)
            conn.commit()

        if output_json:
            initial_output = os.path.join(output_json, file_name.replace('.pm4', '_initial_analysis.json').replace('.adt', '_initial_analysis.json').replace('.pd4', '_initial_analysis.json'))
            detailed_output = os.path.join(output_json, file_name.replace('.pm4', '_detailed_analysis.json').replace('.adt', '_detailed_analysis.json').replace('.pd4', '_detailed_analysis.json'))

            save_json(parsed_data, initial_output)
            save_json(detailed_data, detailed_output)
            logging.info(f"Saved JSON analysis files for {file_name} at {output_json}")

    except Exception as e:
        logging.error(f"Failed to process file {input_file}: {e}")
    finally:
        conn.close()

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
        chunk_size = int.from_bytes(data[offset+4:offset+8], byteorder='little')
        chunk_data = data[offset+8:offset+8 + chunk_size]
        offset += 8 + chunk_size

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

    if os.path.isdir(args.input_path):
        files = [os.path.join(root, file) for root, _, files in os.walk(args.input_path) for file in files if file.lower().endswith(('.pm4', '.pd4', '.adt'))]
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(process_file, file, args.output_dir, args.output_json) for file in files]
            for future in futures:
                future.result()  # Wait for all files to be processed
    else:
        process_file(args.input_path, args.output_dir, args.output_json)

    if args.export_json:
        db_files = [os.path.join(args.output_dir, f) for f in os.listdir(args.output_dir) if f.endswith('.db')]
        for db_file in db_files:
            export_to_json(db_file, args.export_json)

if __name__ == "__main__":
    main()
