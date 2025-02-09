#!/usr/bin/env python3
import os
import json
import sqlite3
import logging
import argparse
import struct
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from pm4_chunk_decoders import pm4_chunk_decoders
from adt_chunk_decoders import adt_chunk_decoders
from pd4_chunk_decoders import pd4_chunk_decoders
from wmo_root_chunk_decoders import wmo_root_chunk_decoders
from wmo_group_chunk_decoders import wmo_group_chunk_decoders
from common_helpers import ensure_folder_exists, reverse_chunk_id

# Setup logging with a timestamped log file
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = f'processing_{timestamp}.log'
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s', handlers=[
    logging.FileHandler(log_file),
    logging.StreamHandler()
])

def read_chunks(file_path):
    """Read file and return a list of chunks with id, size, data (in hex), and a count for each chunk id."""
    file_size = os.path.getsize(file_path)
    with open(file_path, "rb") as f:
        data = f.read()
    offset = 0
    chunks = []
    chunk_count = defaultdict(int)
    while offset < file_size:
        chunk_id = data[offset:offset+4].decode('utf-8')
        chunk_size = struct.unpack_from('I', data, offset+4)[0]
        chunk_data = data[offset+8:offset+8+chunk_size]
        chunk_count[chunk_id] += 1
        chunks.append({
            'id': chunk_id,
            'size': chunk_size,
            'data': chunk_data.hex(),
            'count': chunk_count[chunk_id]
        })
        logging.info(f"Read chunk: {chunk_id} (Size: {chunk_size}) Count: {chunk_count[chunk_id]}")
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS initial_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT,
                chunk_id TEXT,
                size INTEGER,
                data TEXT,
                count INTEGER
            )
        """)
        conn.commit()
        return conn, cursor
    except sqlite3.OperationalError as e:
        logging.error(f"Unable to open database file: {db_path}. Error: {e}")
        raise

def insert_chunk_field_batch(cursor, batch):
    formatted_batch = [
        (file_name, chunk_id, record_index, field_name, convert_to_json(field_value), field_type)
        for file_name, chunk_id, record_index, field_name, field_value, field_type in batch
    ]
    cursor.executemany("""
        INSERT INTO chunk_fields (file_name, chunk_id, record_index, field_name, field_value, field_type) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, formatted_batch)
    logging.info(f"Inserted {len(batch)} records in batch")

def insert_initial_analysis(cursor, file_name, chunks):
    batch = [
        (file_name, chunk['id'], chunk['size'], chunk['data'], chunk['count'])
        for chunk in chunks
    ]
    cursor.executemany("""
        INSERT INTO initial_analysis (file_name, chunk_id, size, data, count) 
        VALUES (?, ?, ?, ?, ?)
    """, batch)
    logging.info(f"Inserted {len(batch)} initial analysis records")

def decode_chunks(chunks, decoders):
    """Decode each chunk using the provided decoders mapping."""
    detailed_chunks = []
    for chunk in chunks:
        chunk_id = chunk['id']
        chunk_data = bytes.fromhex(chunk['data'])
        decoder = decoders.get(chunk_id) or decoders.get(reverse_chunk_id(chunk_id))
        if decoder:
            try:
                decoded_data, _ = decoder(chunk_data, 0)
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
                "data": {"raw_data": chunk_data.hex()}
            })
    return detailed_chunks

def parse_and_split_fields(data, record_index):
    """Flatten dictionary or list data into key/value pairs."""
    fields = []
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                fields.extend(parse_and_split_fields(value, record_index))
            else:
                fields.append((key, value))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            fields.append((f'list_item_{i}', item))
    return fields

def process_file(input_file, output_dir, output_json):
    file_name = os.path.basename(input_file)
    db_path = os.path.join(output_dir, f'{os.path.splitext(file_name)[0]}.db')
    conn, cursor = create_database(db_path)

    try:
        # Read file and insert initial analysis data
        chunks = read_chunks(input_file)
        insert_initial_analysis(cursor, file_name, chunks)

        # Select appropriate decoders based on file extension
        ext = file_name.lower()
        if ext.endswith('adt'):
            decoders = adt_chunk_decoders
        elif ext.endswith('pd4'):
            decoders = pd4_chunk_decoders
        elif ext.endswith('wmo'):
            decoders = wmo_group_chunk_decoders if "_group" in ext else wmo_root_chunk_decoders
        else:
            decoders = pm4_chunk_decoders

        detailed_data = decode_chunks(chunks, decoders)

        # Process detailed data and insert fields in batches
        batch = []
        for record_index, chunk in enumerate(detailed_data):
            chunk_id = chunk['id']
            fields = parse_and_split_fields(chunk['data'], record_index)
            for field_name, field_value in fields:
                field_type = analyze_data_type(field_value)
                batch.append((file_name, chunk_id, record_index, field_name, field_value, field_type))
            if len(batch) >= 1000:
                insert_chunk_field_batch(cursor, batch)
                conn.commit()
                batch = []
        if batch:
            insert_chunk_field_batch(cursor, batch)
            conn.commit()

        if output_json:
            base = os.path.splitext(file_name)[0]
            initial_output = os.path.join(output_json, f"{base}_initial_analysis.json")
            detailed_output = os.path.join(output_json, f"{base}_detailed_analysis.json")
            save_json(chunks, initial_output)
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
    cursor.execute("SELECT file_name, chunk_id, record_index, field_name, field_value, field_type FROM chunk_fields")
    rows = cursor.fetchall()

    data = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    for file_name, chunk_id, record_index, field_name, field_value, field_type in rows:
        data[file_name][chunk_id][record_index][field_name] = {
            "value": json.loads(field_value),
            "type": field_type
        }

    for file_name, chunks in data.items():
        output_file = os.path.join(output_dir, f"{file_name}_exported.json")
        save_json(chunks, output_file)
        logging.info(f"Exported data to {output_file}")

    conn.close()

def main():
    parser = argparse.ArgumentParser(
        description="Process PM4, PD4, ADT, and WMO files, store data in SQLite databases, and optionally export to JSON."
    )
    parser.add_argument("input_path", type=str, help="Path to the input file or directory.")
    parser.add_argument("output_dir", type=str, help="Path to the output directory.")
    parser.add_argument("--output_json", type=str, help="Directory to save JSON analysis files.")
    parser.add_argument("--export_json", type=str, help="Directory to export data from the database to JSON files.")
    args = parser.parse_args()

    ensure_folder_exists(args.output_dir)

    if os.path.isdir(args.input_path):
        files = [
            os.path.join(root, file)
            for root, _, files in os.walk(args.input_path)
            for file in files if file.lower().endswith(('.pm4', '.pd4', '.adt', '.wmo'))
        ]
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
