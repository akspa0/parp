#!/usr/bin/env python3
"""
PM4/PD4 File Analyzer
Analyzes PM4 and PD4 files, storing structured information into SQLite databases
Can be used standalone or as a module with other ADT analysis tools

Usage:
    python pm4_pd4_analyzer.py <input_path> [options]

Arguments:
    input_path             Directory containing PM4/PD4 files or a single file

Options:
    --output DIR           Output directory for databases (default: output in current directory)
    --batch-size N         Number of records to process in each batch (default: 1000)
    --skip-blobs           Skip binary blob fields to reduce output size
    --json                 Also output JSON files with decoded data
    --db-name NAME         Custom database filename (default: based on input filename)
    --clean                Delete existing output before processing
"""

import os
import sys
import json
import sqlite3
import logging
import argparse
import struct
import gc
from datetime import datetime
from collections import defaultdict
import concurrent.futures

# Import the chunk decoders from pm4-tool
# Note: These imports assume the decoder modules are in the same directory
try:
    from pm4_chunk_decoders import pm4_chunk_decoders
    from pd4_chunk_decoders import pd4_chunk_decoders
    from common_helpers import ensure_folder_exists, reverse_chunk_id
except ImportError:
    # If modules not found, define placeholders with essential functionality
    def reverse_chunk_id(chunk_id):
        return chunk_id[::-1]

    def ensure_folder_exists(folder):
        if not os.path.exists(folder):
            os.makedirs(folder)

    # Define empty decoders which will be populated later
    pm4_chunk_decoders = {}
    pd4_chunk_decoders = {}

def setup_logging(log_dir=None):
    """Set up logging with timestamped file and console output"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if log_dir:
        ensure_folder_exists(log_dir)
        log_file = os.path.join(log_dir, f"pm4_pd4_analyzer_{timestamp}.log")
    else:
        log_file = f"pm4_pd4_analyzer_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger('pm4_pd4_analyzer')

def setup_database(db_path):
    """Set up SQLite database for storing PM4/PD4 data"""
    ensure_folder_exists(os.path.dirname(db_path))
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create chunk_data table for raw chunk information
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chunk_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_name TEXT,
        chunk_id TEXT,
        chunk_size INTEGER,
        raw_data BLOB
    )
    """)
    
    # Create decoded_fields table for structured field data
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS decoded_fields (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_name TEXT,
        chunk_id TEXT,
        record_index INTEGER,
        field_name TEXT,
        field_value TEXT,
        field_type TEXT
    )
    """)
    
    # Create file_metadata table for file-level information
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS file_metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_name TEXT,
        file_path TEXT,
        file_size INTEGER,
        file_type TEXT,
        chunk_count INTEGER,
        processed_timestamp TEXT
    )
    """)
    
    conn.commit()
    return conn, cursor

def read_chunks(file_path):
    """Read PM4/PD4 file and extract its chunks"""
    try:
        file_size = os.path.getsize(file_path)
        with open(file_path, "rb") as f:
            data = f.read()
        
        offset = 0
        chunks = []
        chunk_count = defaultdict(int)
        
        while offset < file_size:
            if offset + 8 > file_size:
                logging.warning(f"Incomplete chunk header at offset {offset}")
                break
                
            chunk_id = data[offset:offset+4].decode('utf-8', errors='replace')
            chunk_size = struct.unpack_from('<I', data, offset+4)[0]
            
            if offset + 8 + chunk_size > file_size:
                logging.warning(f"Chunk {chunk_id} extends beyond end of file")
                break
                
            chunk_data = data[offset+8:offset+8+chunk_size]
            chunk_count[chunk_id] += 1
            
            chunks.append({
                'id': chunk_id,
                'size': chunk_size,
                'data': chunk_data,
                'offset': offset
            })
            
            logging.debug(f"Read chunk: {chunk_id} (Size: {chunk_size}) at offset {offset}")
            offset += 8 + chunk_size
        
        logging.info(f"Read {len(chunks)} chunks from {file_path}")
        return chunks, chunk_count
    except Exception as e:
        logging.error(f"Error reading chunks from {file_path}: {e}")
        return [], {}

def decode_chunk(chunk_id, chunk_data, decoders):
    """Decode a chunk using the appropriate decoder function"""
    decoder = decoders.get(chunk_id) or decoders.get(reverse_chunk_id(chunk_id))
    
    if decoder:
        try:
            decoded_data, _ = decoder(chunk_data, 0)
            return decoded_data
        except struct.error as e:
            logging.error(f"Error decoding chunk {chunk_id}: {e}")
            return {"error": str(e), "raw_data": chunk_data.hex()}
    else:
        logging.warning(f"No decoder for chunk: {chunk_id}")
        return {"raw_data": chunk_data.hex()}

def extract_fields(data, prefix=""):
    """Recursively extract fields from nested data structures"""
    fields = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            field_name = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, (dict, list)):
                fields.extend(extract_fields(value, field_name))
            else:
                fields.append((field_name, value, type(value).__name__))
    
    elif isinstance(data, list):
        for i, item in enumerate(data):
            field_name = f"{prefix}[{i}]"
            
            if isinstance(item, (dict, list)):
                fields.extend(extract_fields(item, field_name))
            else:
                fields.append((field_name, item, type(item).__name__))
    
    return fields

def insert_chunk_data(conn, cursor, file_name, chunks, batch_size=1000):
    """Insert raw chunk data into the database"""
    batch = []
    
    for chunk in chunks:
        batch.append((
            file_name,
            chunk['id'],
            chunk['size'],
            chunk['data']
        ))
        
        if len(batch) >= batch_size:
            cursor.executemany("""
                INSERT INTO chunk_data (file_name, chunk_id, chunk_size, raw_data)
                VALUES (?, ?, ?, ?)
            """, batch)
            conn.commit()
            batch = []
            
            # Force garbage collection
            gc.collect()
    
    if batch:
        cursor.executemany("""
            INSERT INTO chunk_data (file_name, chunk_id, chunk_size, raw_data)
            VALUES (?, ?, ?, ?)
        """, batch)
        conn.commit()

def insert_decoded_fields(conn, cursor, file_name, decoded_chunks, batch_size=1000):
    """Insert decoded field data into the database"""
    batch = []
    
    for chunk in decoded_chunks:
        chunk_id = chunk['id']
        record_index = chunk.get('index', 0)
        data = chunk['data']
        
        fields = extract_fields(data)
        
        for field_name, field_value, field_type in fields:
            # Convert non-serializable values to strings
            if not isinstance(field_value, (str, int, float, bool, type(None))):
                field_value = str(field_value)
                
            batch.append((
                file_name,
                chunk_id,
                record_index,
                field_name,
                json.dumps(field_value),
                field_type
            ))
            
            if len(batch) >= batch_size:
                cursor.executemany("""
                    INSERT INTO decoded_fields (file_name, chunk_id, record_index, field_name, field_value, field_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, batch)
                conn.commit()
                batch = []
                
                # Force garbage collection
                gc.collect()
    
    if batch:
        cursor.executemany("""
            INSERT INTO decoded_fields (file_name, chunk_id, record_index, field_name, field_value, field_type)
            VALUES (?, ?, ?, ?, ?, ?)
        """, batch)
        conn.commit()

def insert_file_metadata(conn, cursor, file_path, file_type, chunk_count):
    """Insert file metadata into the database"""
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    total_chunks = sum(chunk_count.values())
    
    cursor.execute("""
        INSERT INTO file_metadata (file_name, file_path, file_size, file_type, chunk_count, processed_timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        file_name,
        file_path,
        file_size,
        file_type,
        total_chunks,
        datetime.now().isoformat()
    ))
    conn.commit()

def save_json(data, output_file):
    """Save data to a JSON file"""
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def process_file(file_path, output_dir, output_json=None, db_name=None, batch_size=1000, skip_blobs=False):
    """Process a single PM4/PD4 file"""
    logger = logging.getLogger('pm4_pd4_analyzer')
    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_name)[1].lower()
    
    # Determine file type and select appropriate decoders
    if file_ext == '.pm4':
        file_type = 'PM4'
        decoders = pm4_chunk_decoders
    elif file_ext == '.pd4':
        file_type = 'PD4'
        decoders = pd4_chunk_decoders
    else:
        logger.warning(f"Unsupported file type: {file_ext}")
        return False
    
    logger.info(f"Processing {file_type} file: {file_name}")
    
    # Set up database
    if db_name:
        db_path = os.path.join(output_dir, db_name)
    else:
        db_path = os.path.join(output_dir, f"{os.path.splitext(file_name)[0]}.db")
    
    conn, cursor = setup_database(db_path)
    
    try:
        # Read and store chunks
        chunks, chunk_count = read_chunks(file_path)
        
        if not chunks:
            logger.error(f"No chunks found in {file_path}")
            return False
        
        # Insert file metadata
        insert_file_metadata(conn, cursor, file_path, file_type, chunk_count)
        
        # Insert raw chunk data if not skipping BLOBs
        if not skip_blobs:
            insert_chunk_data(conn, cursor, file_name, chunks, batch_size)
        
        # Decode chunks and insert structured data
        decoded_chunks = []
        for chunk in chunks:
            decoded_data = decode_chunk(chunk['id'], chunk['data'], decoders)
            
            # Handle both list and dictionary results
            if isinstance(decoded_data, list):
                for i, entry in enumerate(decoded_data):
                    decoded_chunks.append({
                        'id': chunk['id'],
                        'index': i,
                        'data': entry
                    })
            else:
                decoded_chunks.append({
                    'id': chunk['id'],
                    'index': 0,
                    'data': decoded_data
                })
        
        insert_decoded_fields(conn, cursor, file_name, decoded_chunks, batch_size)
        
        # Save to JSON if requested
        if output_json:
            ensure_folder_exists(output_json)
            json_file = os.path.join(output_json, f"{os.path.splitext(file_name)[0]}_analysis.json")
            
            # Format data for JSON output
            json_data = {
                'file_name': file_name,
                'file_type': file_type,
                'chunk_count': chunk_count,
                'chunks': decoded_chunks
            }
            
            save_json(json_data, json_file)
            logger.info(f"Saved JSON analysis to {json_file}")
        
        logger.info(f"Successfully processed {file_name}")
        return True
    
    except Exception as e:
        logger.error(f"Error processing {file_name}: {e}")
        return False
    
    finally:
        conn.close()

def process_directory(input_dir, output_dir, output_json=None, batch_size=1000, skip_blobs=False, max_workers=None):
    """Process all PM4/PD4 files in a directory"""
    logger = logging.getLogger('pm4_pd4_analyzer')
    
    # Find all PM4/PD4 files
    pm4_pd4_files = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith(('.pm4', '.pd4')):
                pm4_pd4_files.append(os.path.join(root, file))
    
    if not pm4_pd4_files:
        logger.warning(f"No PM4/PD4 files found in {input_dir}")
        return False
    
    logger.info(f"Found {len(pm4_pd4_files)} PM4/PD4 files in {input_dir}")
    
    # Process files concurrently
    success_count = 0
    num_workers = max_workers if max_workers else min(os.cpu_count(), len(pm4_pd4_files))
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = []
        
        for file_path in pm4_pd4_files:
            future = executor.submit(
                process_file,
                file_path,
                output_dir,
                output_json,
                None,  # db_name
                batch_size,
                skip_blobs
            )
            futures.append(future)
        
        for future in concurrent.futures.as_completed(futures):
            if future.result():
                success_count += 1
    
    logger.info(f"Successfully processed {success_count} out of {len(pm4_pd4_files)} files")
    return success_count > 0

def main():
    """Main entry point for the PM4/PD4 analyzer"""
    parser = argparse.ArgumentParser(description="Analyze PM4 and PD4 files")
    parser.add_argument("input_path", help="Path to PM4/PD4 file or directory containing files")
    parser.add_argument("--output", default="output", help="Output directory for databases")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for database operations")
    parser.add_argument("--skip-blobs", action="store_true", help="Skip storing binary blob data")
    parser.add_argument("--json", action="store_true", help="Also output JSON files with decoded data")
    parser.add_argument("--db-name", help="Custom database filename (default: based on input filename)")
    parser.add_argument("--clean", action="store_true", help="Delete existing output before processing")
    parser.add_argument("--max-workers", type=int, help="Maximum number of worker threads")
    
    args = parser.parse_args()
    
    # Set up logging
    log_dir = os.path.join(args.output, "logs")
    logger = setup_logging(log_dir)
    
    # Create output directory
    ensure_folder_exists(args.output)
    
    # Clean output directory if requested
    if args.clean and os.path.exists(args.output):
        logger.info(f"Cleaning output directory: {args.output}")
        for file in os.listdir(args.output):
            if file.endswith('.db') or file.endswith('.json'):
                os.remove(os.path.join(args.output, file))
    
    # Set JSON output directory if requested
    output_json = os.path.join(args.output, "json") if args.json else None
    
    # Process input path
    if os.path.isdir(args.input_path):
        success = process_directory(
            args.input_path,
            args.output,
            output_json,
            args.batch_size,
            args.skip_blobs,
            args.max_workers
        )
    elif os.path.isfile(args.input_path):
        success = process_file(
            args.input_path,
            args.output,
            output_json,
            args.db_name,
            args.batch_size,
            args.skip_blobs
        )
    else:
        logger.error(f"Input path not found: {args.input_path}")
        return 1
    
    if success:
        logger.info("Processing completed successfully")
        return 0
    else:
        logger.error("Processing failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
