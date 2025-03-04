#!/usr/bin/env python3
"""
Memory-Efficient DB to JSON Converter
Converts SQLite database files from the ADT analyzer to JSON format with low memory usage

Usage:
    python db_to_json.py <input_directory> [options]

Arguments:
    input_directory        Directory containing SQLite database (.db) files to convert

Options:
    --output FILE          Output JSON file path (default: master_export.json in input directory)
    --format FORMAT        Output format: 'pretty' or 'compact' (default: pretty)
    --tables TABLES        Comma-separated list of tables to extract (default: all)
    --batch-size N         Number of rows to process in each batch (default: 1000)
    --skip-blobs           Skip binary blob fields to reduce output size
    --workers N            Number of worker threads to use (default: CPU count)
    --summary-only         Only include summary information, not actual row data
    --incremental          Process one database at a time to reduce memory usage
"""

import os
import sys
import json
import sqlite3
import argparse
import base64
import threading
import concurrent.futures
import gc
import logging
from datetime import datetime
from collections import defaultdict

def setup_logging():
    """Set up basic logging"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"db_to_json_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger('db_to_json')

def list_tables(db_path):
    """List all tables in a SQLite database"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables
    except sqlite3.Error as e:
        logging.error(f"Error listing tables in {db_path}: {e}")
        return []

def get_table_schema(db_path, table_name):
    """Get the schema for a specific table"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get column information
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        # Get create statement
        cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        create_sql = cursor.fetchone()[0]
        
        # Get foreign keys
        cursor.execute(f"PRAGMA foreign_key_list({table_name})")
        foreign_keys = cursor.fetchall()
        
        conn.close()
        
        return {
            'columns': columns,
            'create_sql': create_sql,
            'foreign_keys': foreign_keys
        }
    except sqlite3.Error as e:
        logging.error(f"Error getting schema for table {table_name} in {db_path}: {e}")
        return {}

def get_table_row_count(db_path, table_name):
    """Get the total number of rows in a table"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except sqlite3.Error as e:
        logging.error(f"Error getting row count for table {table_name} in {db_path}: {e}")
        return 0

def get_table_batch(db_path, table_name, batch_size, offset, skip_blobs=False):
    """Get a batch of rows from a table"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get column information
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = [dict(row) for row in cursor.fetchall()]
        column_types = {col['name']: col['type'].upper() for col in columns_info}
        column_names = [col['name'] for col in columns_info]
        
        # Fetch batch of rows
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset}")
        rows = []
        
        for row in cursor.fetchall():
            row_dict = {}
            for key in row.keys():
                value = row[key]
                
                # Handle blob data
                if value is not None and isinstance(value, bytes):
                    if skip_blobs:
                        value = f"<BLOB data, {len(value)} bytes>"
                    else:
                        # Convert binary data to base64
                        value = base64.b64encode(value).decode('utf-8')
                
                row_dict[key] = value
            
            rows.append(row_dict)
        
        conn.close()
        return rows, column_names, column_types
    except sqlite3.Error as e:
        logging.error(f"Error getting batch from table {table_name} in {db_path}: {e}")
        return [], [], {}

def get_table_summary(db_path, table_name):
    """Get summary information about a table without retrieving all rows"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get column information
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = cursor.fetchall()
        column_types = {col[1]: col[2].upper() for col in columns_info}
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        
        # Get sample data (first row)
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
        sample_row = cursor.fetchone()
        
        # Get create statement
        cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        create_sql = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'column_types': column_types,
            'row_count': row_count,
            'sample_row': sample_row,
            'create_sql': create_sql
        }
    except sqlite3.Error as e:
        logging.error(f"Error getting summary for table {table_name} in {db_path}: {e}")
        return {
            'column_types': {},
            'row_count': 0,
            'sample_row': None,
            'create_sql': ""
        }

def process_table_in_batches(db_path, table_name, batch_size, skip_blobs=False, json_file=None):
    """Process a table in batches to minimize memory usage"""
    logger = logging.getLogger('db_to_json')
    
    # Get total row count
    total_rows = get_table_row_count(db_path, table_name)
    logger.info(f"Processing table {table_name} in {os.path.basename(db_path)} - {total_rows} total rows")
    
    if total_rows == 0:
        return {
            'table_name': table_name,
            'column_types': {},
            'column_names': [],
            'total_rows': 0,
            'rows': []
        }
    
    # Process first batch to get column information
    first_batch, column_names, column_types = get_table_batch(db_path, table_name, 1, 0, skip_blobs)
    
    # Initialize result
    result = {
        'table_name': table_name,
        'column_types': column_types,
        'column_names': column_names,
        'total_rows': total_rows,
        'rows': []
    }
    
    # If writing directly to a JSON file
    is_writing_to_file = json_file is not None
    if is_writing_to_file:
        # Write the table header
        with open(json_file, 'w') as f:
            # Write table info but with empty rows array
            result_header = result.copy()
            result_header['rows'] = []  # Empty rows list for header
            json.dump(result_header, f)
            f.write('\n')  # Line-delimited JSON
    
    # Process in batches
    offset = 0
    processed_rows = 0
    
    while offset < total_rows:
        # Get batch of rows
        rows, _, _ = get_table_batch(db_path, table_name, batch_size, offset, skip_blobs)
        processed_rows += len(rows)
        
        # If writing to a file, append this batch
        if is_writing_to_file:
            with open(json_file, 'a') as f:
                for row in rows:
                    f.write(json.dumps(row) + '\n')
        else:
            # If accumulating in memory, add to result
            result['rows'].extend(rows)
        
        logger.info(f"Processed {processed_rows}/{total_rows} rows from table {table_name}")
        
        # Force garbage collection to free memory
        rows = None
        gc.collect()
        
        # Move to next batch
        offset += batch_size
    
    return result

def process_database_in_batches(db_path, output_dir, tables_to_extract=None, batch_size=1000, 
                              skip_blobs=False, summary_only=False, incremental=False):
    """Process a single database in memory-efficient batches"""
    logger = logging.getLogger('db_to_json')
    
    db_name = os.path.basename(db_path)
    logger.info(f"Processing database: {db_name}")
    
    # Get list of tables
    all_tables = list_tables(db_path)
    if not all_tables:
        logger.warning(f"No tables found in {db_name}")
        return None
    
    # Determine which tables to process
    if tables_to_extract:
        tables = [t for t in all_tables if t in tables_to_extract]
    else:
        tables = all_tables
    
    # Create output directory for this database
    db_output_dir = os.path.join(output_dir, os.path.splitext(db_name)[0])
    if incremental:
        os.makedirs(db_output_dir, exist_ok=True)
    
    # Process each table
    db_data = {
        "database": db_name,
        "tables": {}
    }
    
    for table in tables:
        logger.info(f"Processing table {table} in {db_name}")
        
        if summary_only:
            # Get just summary information
            summary = get_table_summary(db_path, table)
            db_data["tables"][table] = {
                "column_types": summary['column_types'],
                "row_count": summary['row_count'],
                "create_sql": summary['create_sql'],
                "sample_row": summary['sample_row']
            }
        else:
            # Process in batches
            if incremental:
                # Write directly to a file
                table_file = os.path.join(db_output_dir, f"{table}.json")
                table_data = process_table_in_batches(db_path, table, batch_size, skip_blobs, table_file)
                # Store just the metadata
                db_data["tables"][table] = {
                    "column_types": table_data['column_types'],
                    "column_names": table_data['column_names'],
                    "total_rows": table_data['total_rows'],
                    "file_path": table_file
                }
            else:
                # Accumulate in memory
                table_data = process_table_in_batches(db_path, table, batch_size, skip_blobs)
                db_data["tables"][table] = {
                    "column_types": table_data['column_types'],
                    "column_names": table_data['column_names'],
                    "total_rows": table_data['total_rows'],
                    "rows": table_data['rows']
                }
        
        # Force garbage collection
        gc.collect()
    
    # Write database metadata
    if incremental:
        db_meta_file = os.path.join(db_output_dir, "_metadata.json")
        with open(db_meta_file, 'w') as f:
            json.dump(db_data, f, indent=2)
    
    return db_data

def write_json_output(data, output_path, indent=2):
    """Write data to a JSON file"""
    logger = logging.getLogger('db_to_json')
    
    try:
        # Create directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=indent)
        
        logger.info(f"Successfully wrote output to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error writing to {output_path}: {e}")
        return False

def process_directory(input_dir, output_path, format='pretty', tables_to_extract=None, 
                     batch_size=1000, skip_blobs=False, workers=None, summary_only=False,
                     incremental=False):
    """Process all database files in a directory and combine them into a single JSON file"""
    logger = logging.getLogger('db_to_json')
    
    # Find all .db files in the input directory
    db_files = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.endswith('.db')]
    
    if not db_files:
        logger.error(f"No .db files found in {input_dir}")
        return False
    
    logger.info(f"Found {len(db_files)} database files to process")
    
    # Create output directory for intermediate files if using incremental mode
    if incremental:
        output_dir = os.path.dirname(output_path)
        if not output_dir:
            output_dir = "."
        os.makedirs(output_dir, exist_ok=True)
        
        # Create index file
        index_data = {
            "export_date": datetime.now().isoformat(),
            "databases": [os.path.basename(db) for db in db_files],
            "directory_structure": "Each database has its own directory. Tables are stored in individual JSON files."
        }
        
        index_path = os.path.join(output_dir, "index.json")
        with open(index_path, 'w') as f:
            json.dump(index_data, f, indent=2)
        
        logger.info(f"Created index file at {index_path}")
        
        # Process each database sequentially to save memory
        for db_path in db_files:
            process_database_in_batches(
                db_path,
                output_dir,
                tables_to_extract,
                batch_size,
                skip_blobs,
                summary_only,
                incremental
            )
            
            # Force garbage collection
            gc.collect()
        
        logger.info(f"Completed incremental processing of {len(db_files)} databases")
        return True
    
    # Set up a thread pool to process databases in parallel (non-incremental mode)
    num_workers = workers if workers else min(os.cpu_count(), len(db_files))
    logger.info(f"Using {num_workers} worker threads")
    
    combined_data = {
        "export_date": datetime.now().isoformat(),
        "databases": {}
    }
    
    # Process databases in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        # Submit tasks
        future_to_db = {
            executor.submit(
                process_database_in_batches, 
                db_path, 
                None,  # No output directory for non-incremental mode
                tables_to_extract, 
                batch_size, 
                skip_blobs, 
                summary_only,
                False  # Not incremental within this execution
            ): db_path for db_path in db_files
        }
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_db):
            db_path = future_to_db[future]
            db_name = os.path.basename(db_path)
            
            try:
                db_data = future.result()
                if db_data:
                    combined_data["databases"][db_name] = db_data
                    logger.info(f"Added {db_name} to master JSON")
                    
                    # Force garbage collection after each database is processed
                    db_data = None
                    gc.collect()
            except Exception as e:
                logger.error(f"Error processing {db_name}: {e}")
    
    # Set JSON indent based on format
    indent = 2 if format == 'pretty' else None
    
    # Write the combined output
    success = write_json_output(combined_data, output_path, indent)
    
    return success

def main():
    """Main entry point for the DB to JSON converter"""
    parser = argparse.ArgumentParser(description="Convert SQLite database files to JSON format")
    parser.add_argument("input_directory", help="Directory containing SQLite database (.db) files to convert")
    parser.add_argument("--output", help="Output JSON file path (default: master_export.json in input directory)")
    parser.add_argument("--format", choices=["pretty", "compact"], default="pretty", 
                        help="Output format: 'pretty' or 'compact' (default: pretty)")
    parser.add_argument("--tables", help="Comma-separated list of tables to extract (default: all)")
    parser.add_argument("--batch-size", type=int, default=1000, 
                        help="Number of rows to process in each batch (default: 1000)")
    parser.add_argument("--skip-blobs", action="store_true", 
                        help="Skip binary blob fields to reduce output size")
    parser.add_argument("--workers", type=int, help="Number of worker threads to use (default: CPU count)")
    parser.add_argument("--summary-only", action="store_true",
                        help="Only include summary information, not actual row data")
    parser.add_argument("--incremental", action="store_true",
                        help="Process one database at a time to reduce memory usage")
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging()
    
    # Check if input directory exists
    if not os.path.exists(args.input_directory):
        logger.error(f"Input directory {args.input_directory} does not exist")
        return 1
    
    # Set default output path if not specified
    if not args.output:
        args.output = os.path.join(args.input_directory, "master_export.json")
    
    # Parse tables list if provided
    tables_to_extract = None
    if args.tables:
        tables_to_extract = [t.strip() for t in args.tables.split(',')]
    
    # Process the input directory
    success = process_directory(
        args.input_directory,
        args.output,
        args.format,
        tables_to_extract,
        args.batch_size,
        args.skip_blobs,
        args.workers,
        args.summary_only,
        args.incremental
    )
    
    if success:
        logger.info("Export completed successfully")
        return 0
    else:
        logger.error("Export failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
