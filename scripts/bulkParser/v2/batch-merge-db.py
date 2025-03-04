#!/usr/bin/env python3
"""
Batch Merge DB
High-performance, multi-threaded tool to merge multiple SQLite databases into a master database

Usage:
    python batch_merge_db.py <input_directory> [options]

Arguments:
    input_directory        Directory containing SQLite database (.db) files to merge

Options:
    --output FILE          Output master database file path (default: master.db in input directory)
    --batch-size N         Number of records to process in each batch (default: 5000)
    --workers N            Number of worker threads to use (default: CPU count)
    --skip-tables TABLES   Comma-separated list of tables to skip
    --only-tables TABLES   Comma-separated list of tables to include (overrides skip-tables)
    --skip-blobs           Skip tables with BLOB columns to reduce processing time
    --vacuum               Run VACUUM on the master database after merging
    --clean                Delete existing master database if it exists
    --dry-run              Show what would be done without actually merging
"""

import os
import sys
import sqlite3
import argparse
import logging
import threading
import time
import queue
import concurrent.futures
from datetime import datetime
from collections import defaultdict

def setup_logging():
    """Set up logging with timestamped file and console output"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"batch_merge_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger('batch_merge')

def get_database_schema(db_path):
    """Get the schema for all tables in a database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]
    
    schema = {}
    for table in tables:
        # Get column info
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        
        # Get create statement
        cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
        create_sql = cursor.fetchone()[0]
        
        # Get foreign keys
        cursor.execute(f"PRAGMA foreign_key_list({table})")
        foreign_keys = cursor.fetchall()
        
        schema[table] = {
            'columns': columns,
            'create_sql': create_sql,
            'foreign_keys': foreign_keys
        }
    
    conn.close()
    return schema

def setup_master_database(master_db_path, schema, skip_tables=None, only_tables=None, skip_blobs=False):
    """Set up the master database with the required schema"""
    conn = sqlite3.connect(master_db_path)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = OFF")
    
    # Determine which tables to include
    tables_to_create = []
    for table, table_schema in schema.items():
        # Skip tables if specified
        if skip_tables and table in skip_tables:
            continue
        
        # Only include specific tables if specified
        if only_tables and table not in only_tables:
            continue
        
        # Check for BLOB columns if skipping blobs
        if skip_blobs:
            has_blobs = any(col[2].upper() == 'BLOB' for col in table_schema['columns'])
            if has_blobs:
                logging.info(f"Skipping table {table} because it contains BLOB columns")
                continue
        
        tables_to_create.append((table, table_schema['create_sql']))
    
    # Create each table
    for table, create_sql in tables_to_create:
        try:
            cursor.execute(create_sql)
            logging.info(f"Created table {table} in master database")
        except sqlite3.Error as e:
            logging.error(f"Error creating table {table}: {e}")
    
    conn.commit()
    conn.close()
    
    return tables_to_create

def get_table_column_names(db_path, table):
    """Get the column names for a specific table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    
    conn.close()
    return columns

def fetch_data_batch(db_path, table, batch_size, offset):
    """Fetch a batch of data from a table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute(f"SELECT * FROM {table} LIMIT {batch_size} OFFSET {offset}")
        batch = cursor.fetchall()
        return batch
    except sqlite3.Error as e:
        logging.error(f"Error fetching batch from {table} in {db_path}: {e}")
        return []
    finally:
        conn.close()

def get_row_count(db_path, table):
    """Get the number of rows in a table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    
    conn.close()
    return count

def insert_batch(master_db_path, table, column_names, batch_data, lock):
    """Insert a batch of data into the master database"""
    conn = sqlite3.connect(master_db_path)
    cursor = conn.cursor()
    
    # Skip 'id' column for inserts if it exists and is an integer primary key
    columns = column_names.copy()
    if 'id' in columns:
        # Check if id is an integer primary key
        cursor.execute(f"PRAGMA table_info({table})")
        table_info = cursor.fetchall()
        for col in table_info:
            if col[1] == 'id' and col[5] == 1:  # 5 is the primary key column
                columns.remove('id')
                break
    
    if not columns:
        logging.error(f"No columns to insert for table {table}")
        conn.close()
        return 0
    
    # Create placeholders for values
    placeholders = ','.join(['?' for _ in columns])
    column_str = ','.join(columns)
    
    # Create a list of tuples with values corresponding to the columns
    values_to_insert = []
    for row in batch_data:
        row_values = []
        for i, col in enumerate(column_names):
            if col in columns:  # Skip id column if removed
                row_values.append(row[i])
        values_to_insert.append(tuple(row_values))
    
    try:
        with lock:
            cursor.executemany(
                f"INSERT INTO {table} ({column_str}) VALUES ({placeholders})",
                values_to_insert
            )
            conn.commit()
            rows_inserted = len(values_to_insert)
    except sqlite3.Error as e:
        logging.error(f"Error inserting batch into {table}: {e}")
        conn.rollback()
        rows_inserted = 0
    
    conn.close()
    return rows_inserted

def process_table(db_path, master_db_path, table, batch_size, db_lock):
    """Process a complete table from a database in batches"""
    row_count = get_row_count(db_path, table)
    if row_count == 0:
        logging.info(f"Table {table} in {os.path.basename(db_path)} is empty, skipping")
        return 0
    
    logging.info(f"Processing {row_count} rows from table {table} in {os.path.basename(db_path)}")
    
    # Get column names
    column_names = get_table_column_names(db_path, table)
    if not column_names:
        logging.error(f"Failed to get column names for table {table}")
        return 0
    
    # Process in batches
    total_inserted = 0
    offset = 0
    
    while offset < row_count:
        batch = fetch_data_batch(db_path, table, batch_size, offset)
        if not batch:
            break
        
        rows_inserted = insert_batch(master_db_path, table, column_names, batch, db_lock)
        total_inserted += rows_inserted
        
        logging.info(f"Inserted {rows_inserted} rows into {table} ({total_inserted}/{row_count})")
        offset += batch_size
    
    return total_inserted

def worker_function(task_queue, result_queue, master_db_path, batch_size, db_lock):
    """Worker function for processing tasks"""
    while True:
        try:
            task = task_queue.get(block=False)
            if task is None:
                break
            
            db_path, table = task
            rows_inserted = process_table(db_path, master_db_path, table, batch_size, db_lock)
            
            result_queue.put((db_path, table, rows_inserted))
            task_queue.task_done()
        except queue.Empty:
            break
        except Exception as e:
            logging.error(f"Error in worker: {e}")
            task_queue.task_done()

def merge_databases(input_dir, master_db_path, batch_size=5000, workers=None, 
                    skip_tables=None, only_tables=None, skip_blobs=False, vacuum=False,
                    dry_run=False):
    """Merge multiple databases into a master database using multi-threading"""
    logger = logging.getLogger('batch_merge')
    
    # Find all .db files in the input directory
    db_files = [os.path.join(input_dir, f) for f in os.listdir(input_dir) 
                if f.endswith('.db') and os.path.join(input_dir, f) != master_db_path]
    
    if not db_files:
        logger.error(f"No .db files found in {input_dir}")
        return False
    
    logger.info(f"Found {len(db_files)} database files to merge")
    
    # Get schema from the first database
    first_db = db_files[0]
    logger.info(f"Using schema from {os.path.basename(first_db)}")
    
    schema = get_database_schema(first_db)
    logger.info(f"Found {len(schema)} tables in schema")
    
    if dry_run:
        logger.info("=== DRY RUN - No changes will be made ===")
        
        # Show tables that would be processed
        tables_to_process = []
        for table in schema.keys():
            if skip_tables and table in skip_tables:
                continue
            if only_tables and table not in only_tables:
                continue
            if skip_blobs:
                has_blobs = any(col[2].upper() == 'BLOB' for col in schema[table]['columns'])
                if has_blobs:
                    continue
            tables_to_process.append(table)
        
        logger.info(f"Would process the following tables: {', '.join(tables_to_process)}")
        logger.info(f"Would process {len(db_files)} database files")
        logger.info(f"Would use batch size of {batch_size} records")
        logger.info(f"Would use {workers if workers else os.cpu_count()} worker threads")
        logger.info(f"Output would be written to {master_db_path}")
        
        # Show estimated row counts
        for table in tables_to_process:
            total_rows = sum(get_row_count(db, table) for db in db_files)
            logger.info(f"Table {table}: approximately {total_rows} rows would be processed")
        
        return True
    
    # Create the master database with the schema
    if not os.path.exists(os.path.dirname(master_db_path)):
        os.makedirs(os.path.dirname(master_db_path), exist_ok=True)
    
    tables_to_create = setup_master_database(master_db_path, schema, skip_tables, only_tables, skip_blobs)
    if not tables_to_create:
        logger.error("No tables to create in master database")
        return False
    
    # Set up task queue
    task_queue = queue.Queue()
    result_queue = queue.Queue()
    
    # Add tasks to the queue
    for db_path in db_files:
        for table, _ in tables_to_create:
            task_queue.put((db_path, table))
    
    # Create a lock for database access
    db_lock = threading.Lock()
    
    # Create worker threads
    num_workers = workers if workers else os.cpu_count()
    threads = []
    
    start_time = time.time()
    
    for _ in range(num_workers):
        thread = threading.Thread(
            target=worker_function,
            args=(task_queue, result_queue, master_db_path, batch_size, db_lock)
        )
        thread.start()
        threads.append(thread)
    
    # Add termination tasks
    for _ in range(num_workers):
        task_queue.put(None)
    
    # Wait for all tasks to complete
    for thread in threads:
        thread.join()
    
    # Process results
    results = {}
    while not result_queue.empty():
        db_path, table, rows = result_queue.get()
        if (db_path, table) not in results:
            results[(db_path, table)] = 0
        results[(db_path, table)] += rows
    
    # Calculate statistics
    total_rows = sum(rows for rows in results.values())
    elapsed_time = time.time() - start_time
    
    logger.info(f"Merged {len(db_files)} databases into {master_db_path}")
    logger.info(f"Inserted {total_rows} total rows")
    logger.info(f"Operation completed in {elapsed_time:.2f} seconds")
    
    # Create indexes on the master database
    conn = sqlite3.connect(master_db_path)
    cursor = conn.cursor()
    
    try:
        # Create indexes on foreign key columns
        for table, table_schema in schema.items():
            if skip_tables and table in skip_tables:
                continue
            if only_tables and table not in only_tables:
                continue
            
            foreign_keys = table_schema['foreign_keys']
            for fk in foreign_keys:
                from_col = fk[3]  # Column in this table
                to_table = fk[2]  # Referenced table
                
                # Create an index on the foreign key column
                index_name = f"idx_{table}_{from_col}"
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table}({from_col})")
                logger.info(f"Created index {index_name} on {table}({from_col})")
    except sqlite3.Error as e:
        logger.error(f"Error creating indexes: {e}")
    
    # Run VACUUM if requested
    if vacuum:
        logger.info("Running VACUUM on master database...")
        cursor.execute("VACUUM")
    
    conn.commit()
    conn.close()
    
    return True

def main():
    """Main entry point for the batch merge tool"""
    parser = argparse.ArgumentParser(description="Merge multiple SQLite databases into a master database")
    parser.add_argument("input_directory", help="Directory containing SQLite database (.db) files to merge")
    parser.add_argument("--output", help="Output master database file path (default: master.db in input directory)")
    parser.add_argument("--batch-size", type=int, default=5000, 
                        help="Number of records to process in each batch (default: 5000)")
    parser.add_argument("--workers", type=int, help="Number of worker threads to use (default: CPU count)")
    parser.add_argument("--skip-tables", help="Comma-separated list of tables to skip")
    parser.add_argument("--only-tables", help="Comma-separated list of tables to include (overrides skip-tables)")
    parser.add_argument("--skip-blobs", action="store_true", 
                        help="Skip tables with BLOB columns to reduce processing time")
    parser.add_argument("--vacuum", action="store_true", 
                        help="Run VACUUM on the master database after merging")
    parser.add_argument("--clean", action="store_true", 
                        help="Delete existing master database if it exists")
    parser.add_argument("--dry-run", action="store_true", 
                        help="Show what would be done without actually merging")
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging()
    
    # Check if input directory exists
    if not os.path.exists(args.input_directory):
        logger.error(f"Input directory {args.input_directory} does not exist")
        return 1
    
    # Set default output path if not specified
    if not args.output:
        args.output = os.path.join(args.input_directory, "master.db")
    
    # Parse table lists if provided
    skip_tables = None
    if args.skip_tables:
        skip_tables = [t.strip() for t in args.skip_tables.split(',')]
    
    only_tables = None
    if args.only_tables:
        only_tables = [t.strip() for t in args.only_tables.split(',')]
    
    # Delete existing database if clean option is specified
    if args.clean and os.path.exists(args.output) and not args.dry_run:
        try:
            os.remove(args.output)
            logger.info(f"Deleted existing database {args.output}")
        except OSError as e:
            logger.error(f"Error deleting existing database {args.output}: {e}")
            return 1
    
    # Merge databases
    success = merge_databases(
        args.input_directory,
        args.output,
        args.batch_size,
        args.workers,
        skip_tables,
        only_tables,
        args.skip_blobs,
        args.vacuum,
        args.dry_run
    )
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
