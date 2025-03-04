#!/usr/bin/env python3
"""
DB to JSON Converter
Converts SQLite database files from the ADT analyzer to JSON format

Usage:
    python db_to_json.py <input_directory> [options]

Arguments:
    input_directory        Directory containing SQLite database (.db) files to convert

Options:
    --output FILE          Output JSON file path (default: master_export.json in input directory)
    --format FORMAT        Output format: 'pretty' or 'compact' (default: pretty)
    --tables TABLES        Comma-separated list of tables to extract (default: all)
    --limit N              Limit number of rows per table (default: no limit)
    --skip-blobs           Skip binary blob fields to reduce output size
    --workers N            Number of worker threads to use (default: CPU count)
    --summary-only         Only include summary information, not actual row data
"""

import os
import sys
import json
import sqlite3
import argparse
import base64
import threading
import concurrent.futures
import logging
from datetime import datetime
from collections import defaultdict

def setup_logging():
    """Set up basic logging"""
    # Create a timestamped output directory for this run
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

def get_table_data(db_path, table_name, limit=None, skip_blobs=False):
    """Get all data from a table with column names"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        cursor = conn.cursor()
        
        # Get column information including types
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = [dict(row) for row in cursor.fetchall()]
        column_types = {col['name']: col['type'].upper() for col in columns_info}
        column_names = [col['name'] for col in columns_info]
        
        # Prepare the query
        query = f"SELECT * FROM {table_name}"
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        results = []
        
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
            
            results.append(row_dict)
        
        # Get row count (may be different from results if limit is used)
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_rows = cursor.fetchone()[0]
        
        conn.close()
        return {
            'column_types': column_types,
            'column_names': column_names,
            'total_rows': total_rows,
            'rows': results
        }
    except sqlite3.Error as e:
        logging.error(f"Error getting data from table {table_name} in {db_path}: {e}")
        return {
            'column_types': {},
            'column_names': [],
            'total_rows': 0,
            'rows': []
        }

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

def process_database(db_path, tables_to_extract=None, limit=None, skip_blobs=False, summary_only=False):
    """Process a single database and extract its tables"""
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
            # Get full table data
            table_data = get_table_data(db_path, table, limit, skip_blobs)
            db_data["tables"][table] = {
                "column_types": table_data['column_types'],
                "column_names": table_data['column_names'],
                "total_rows": table_data['total_rows'],
                "rows": table_data['rows']
            }
    
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
                     limit=None, skip_blobs=False, workers=None, summary_only=False):
    """Process all database files in a directory and combine them into a single JSON file"""
    logger = logging.getLogger('db_to_json')
    
    # Find all .db files in the input directory
    db_files = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.endswith('.db')]
    
    if not db_files:
        logger.error(f"No .db files found in {input_dir}")
        return False
    
    logger.info(f"Found {len(db_files)} database files to process")
    
    # Set up a thread pool to process databases in parallel
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
                process_database, db_path, tables_to_extract, limit, skip_blobs, summary_only
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
    parser.add_argument("--limit", type=int, help="Limit number of rows per table (default: no limit)")
    parser.add_argument("--skip-blobs", action="store_true", 
                        help="Skip binary blob fields to reduce output size")
    parser.add_argument("--workers", type=int, help="Number of worker threads to use (default: CPU count)")
    parser.add_argument("--summary-only", action="store_true",
                        help="Only include summary information, not actual row data")
    
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
        args.limit,
        args.skip_blobs,
        args.workers,
        args.summary_only
    )
    
    if success:
        logger.info("Export completed successfully")
        return 0
    else:
        logger.error("Export failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
