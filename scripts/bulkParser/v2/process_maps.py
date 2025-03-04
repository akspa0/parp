#!/usr/bin/env python3
"""
Map Processor
Recursively processes all map folders in a directory, creating individual databases
and a merged master database.

Usage:
    python process_maps.py <maps_directory> <listfile_path> [options]

Options:
    --master-db NAME       Name of the master database (default: master.db)
    --skip-individual      Skip creating individual map databases
    --skip-master          Skip creating the master database
    --log-level LEVEL      Set logging level (DEBUG, INFO, WARNING, ERROR)
    --no-repair            Disable automatic file path repair attempts
    --clean                Delete existing databases before processing
"""

import os
import sys
import sqlite3
import argparse
import logging
import shutil
import subprocess
import tempfile
import time
import re
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

def setup_logging(log_dir, log_level="INFO"):
    """Set up logging for the map processor"""
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure logging
    log_filename = os.path.join(log_dir, f"map_processor.log")
    
    # Set up the root logger
    logging.basicConfig(
        filename=log_filename,
        filemode='w',
        format='%(asctime)s [%(levelname)s] %(message)s',
        level=getattr(logging, log_level)
    )
    logger = logging.getLogger("map_processor")
    
    # Add console handler
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    console.setLevel(getattr(logging, log_level))
    logger.addHandler(console)
    
    return logger

def find_map_folders(maps_directory):
    """Find all folders that contain ADT files"""
    map_folders = []
    
    for root, dirs, files in os.walk(maps_directory):
        # Check if this directory contains ADT files
        if any(f.lower().endswith('.adt') for f in files):
            map_folders.append(root)
    
    return map_folders

def count_adt_files(directory):
    """Count the number of ADT files in a directory"""
    return sum(1 for f in os.listdir(directory) if f.lower().endswith('.adt'))

def process_map_folder(params):
    """Process a single map folder"""
    map_folder, listfile_path, db_name, output_dir, log_level, no_repair = params
    
    # Create a command to run the main.py script
    # This assumes the main.py is in the same directory as this script
    main_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    
    # Make sure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Create the log directory for this map
    map_name = os.path.basename(map_folder)
    map_log_dir = os.path.join(output_dir, "logs", map_name)
    os.makedirs(map_log_dir, exist_ok=True)
    
    cmd = [
        sys.executable,
        main_script,
        map_folder,
        listfile_path,
        "--db", db_name,
        "--log-dir", map_log_dir
    ]
    
    if log_level:
        cmd.extend(["--log-level", log_level])
    
    if no_repair:
        cmd.append("--no-repair")
    
    # Run the command and capture output
    process = subprocess.Popen(
        cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    
    # Wait for the command to complete
    stdout, stderr = process.communicate()
    
    # Return the results
    return {
        'map_folder': map_folder,
        'db_name': db_name,
        'exit_code': process.returncode,
        'stdout': stdout,
        'stderr': stderr
    }

def get_create_table_sql(db_file):
    """Get CREATE TABLE statements from a database file"""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Get all table creation statements
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = cursor.fetchall()
    
    conn.close()
    return tables

def create_tables_in_master(master_conn, create_statements):
    """Create tables in the master database from CREATE statements"""
    cursor = master_conn.cursor()
    
    for table_name, create_sql in create_statements:
        # Skip the chunks table to reduce database size
        if table_name == 'chunks':
            continue
            
        # Check if the table already exists
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        if not cursor.fetchone():
            cursor.execute(create_sql)
    
    master_conn.commit()

def merge_databases(master_db, db_list, logger):
    """Merge multiple SQLite databases into a master database"""
    logger.info(f"Merging {len(db_list)} databases into {master_db}")
    
    # Make sure the master database exists and has the right schema
    master_conn = sqlite3.connect(master_db)
    
    # Create tables using schema from the first database
    if db_list:
        create_statements = get_create_table_sql(db_list[0])
        create_tables_in_master(master_conn, create_statements)
    else:
        logger.error("No databases to merge")
        master_conn.close()
        return
    
    # Process each database
    for db_file in db_list:
        source_map_name = os.path.basename(os.path.dirname(db_file))
        logger.info(f"Merging database {db_file} ({source_map_name})")
        
        # Connect to the source database
        source_conn = sqlite3.connect(db_file)
        source_cur = source_conn.cursor()
        
        try:
            # Get all tables in the source database
            source_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [table[0] for table in source_cur.fetchall()]
            
            # Skip the chunks table to reduce database size
            if 'chunks' in tables:
                tables.remove('chunks')
            
            # Start a transaction for better performance
            master_conn.execute("BEGIN TRANSACTION")
            
            # Process adt_files table first to establish foreign key references
            if 'adt_files' in tables:
                process_adt_files_table(master_conn, source_conn, source_map_name)
                tables.remove('adt_files')
            
            # Process other tables
            for table_name in tables:
                process_table(master_conn, source_conn, table_name, source_map_name, logger)
            
            # Commit the transaction
            master_conn.commit()
            logger.info(f"Successfully merged {db_file}")
            
        except Exception as e:
            logger.error(f"Error merging {db_file}: {e}")
            master_conn.rollback()
        finally:
            source_conn.close()
    
    # Optimize the master database
    logger.info("Optimizing master database...")
    master_conn.execute("VACUUM")
    master_conn.execute("ANALYZE")
    
    master_conn.close()
    logger.info("Database merge complete")

def process_adt_files_table(master_conn, source_conn, source_map_name):
    """Process the adt_files table to establish foreign key references"""
    master_cur = master_conn.cursor()
    source_cur = source_conn.cursor()
    
    # Get column names for adt_files table
    source_cur.execute("PRAGMA table_info(adt_files)")
    columns = [col[1] for col in source_cur.fetchall()]
    
    # Retrieve all records from source adt_files table
    source_cur.execute(f"SELECT * FROM adt_files")
    for row in source_cur.fetchall():
        # Create a dictionary of column name to value
        record = {columns[i]: row[i] for i in range(len(columns))}
        
        # Check if this record already exists in the master
        master_cur.execute(
            "SELECT id FROM adt_files WHERE name=? AND folder_name=? AND x_coord=? AND y_coord=?",
            (record['name'], record['folder_name'], record['x_coord'], record['y_coord'])
        )
        existing = master_cur.fetchone()
        
        if not existing:
            # Prepare the INSERT statement
            column_str = ', '.join(columns[1:])  # Skip 'id' column
            placeholder_str = ', '.join(['?'] * (len(columns) - 1))
            values = [record[col] for col in columns[1:]]
            
            # Insert the record
            master_cur.execute(
                f"INSERT INTO adt_files ({column_str}) VALUES ({placeholder_str})",
                values
            )

def process_table(master_conn, source_conn, table_name, source_map_name, logger):
    """Process a table for merging into the master database"""
    master_cur = master_conn.cursor()
    source_cur = source_conn.cursor()
    
    # Skip the chunks table to reduce database size
    if table_name == 'chunks':
        return
    
    try:
        # Get column information
        source_cur.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in source_cur.fetchall()]
        
        # Get foreign key information
        source_cur.execute(f"PRAGMA foreign_key_list({table_name})")
        foreign_keys = source_cur.fetchall()
        
        # Create a mapping of columns to their foreign key info
        fk_map = {}
        for fk in foreign_keys:
            from_col = fk[3]  # Column in this table
            to_table = fk[2]  # Referenced table
            to_col = fk[4]    # Referenced column
            fk_map[from_col] = {'table': to_table, 'column': to_col}
        
        # Retrieve all records from source table
        source_cur.execute(f"SELECT * FROM {table_name}")
        records = source_cur.fetchall()
        
        if not records:
            logger.debug(f"Table {table_name} is empty in {source_map_name}")
            return
        
        # Process each record
        for row in records:
            record_dict = {columns[i]: row[i] for i in range(len(columns))}
            
            # Adjust foreign keys to reference master database IDs
            for col, fk_info in fk_map.items():
                if col in record_dict and record_dict[col] is not None:
                    source_id = record_dict[col]
                    
                    if fk_info['table'] == 'adt_files' and fk_info['column'] == 'id':
                        # Get the adt_file details from the source
                        source_cur.execute(f"SELECT name, folder_name, x_coord, y_coord FROM adt_files WHERE id=?", (source_id,))
                        adt_info = source_cur.fetchone()
                        
                        if adt_info:
                            # Find the corresponding record in the master
                            master_cur.execute(
                                "SELECT id FROM adt_files WHERE name=? AND folder_name=? AND x_coord=? AND y_coord=?",
                                adt_info
                            )
                            master_id = master_cur.fetchone()
                            
                            if master_id:
                                record_dict[col] = master_id[0]
                            else:
                                logger.warning(f"Could not find matching adt_file in master for {adt_info}")
                                continue  # Skip this record if we can't resolve the foreign key
            
            # Prepare the INSERT statement
            column_str = ', '.join(columns)
            placeholder_str = ', '.join(['?' if col != 'id' else 'NULL' for col in columns])  # Use NULL for id column
            values = [record_dict[col] for col in columns]
            
            try:
                # Insert the record
                master_cur.execute(
                    f"INSERT INTO {table_name} ({column_str}) VALUES ({placeholder_str})",
                    values
                )
            except sqlite3.Error as e:
                logger.error(f"Error inserting into {table_name}: {e}")
                logger.error(f"Record: {record_dict}")
    
    except Exception as e:
        logger.error(f"Error processing table {table_name}: {e}")
        raise

def main():
    """Main entry point for the map processor"""
    parser = argparse.ArgumentParser(description="Process multiple map folders and merge databases")
    parser.add_argument("maps_directory", help="Directory containing map folders")
    parser.add_argument("listfile_path", help="Path to listfile for file reference checks")
    parser.add_argument("--master-db", default="master.db", help="Name of the master database (default: master.db)")
    parser.add_argument("--skip-individual", action="store_true", help="Skip creating individual map databases")
    parser.add_argument("--skip-master", action="store_true", help="Skip creating the master database")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO", help="Set the logging level")
    parser.add_argument("--no-repair", action="store_true", help="Disable automatic file path repair attempts")
    parser.add_argument("--clean", action="store_true", help="Delete existing databases before processing")
    parser.add_argument("--max-workers", type=int, default=os.cpu_count(), help=f"Maximum number of worker processes (default: {os.cpu_count()})")
    
    args = parser.parse_args()
    
    # Create a timestamped output directory for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"output_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    
    # Setup logging
    log_dir = os.path.join(output_dir, "logs")
    logger = setup_logging(log_dir, args.log_level)
    
    # Display information about the run
    logger.info(f"Map Processor starting")
    logger.info(f"Maps directory: {args.maps_directory}")
    logger.info(f"Listfile: {args.listfile_path}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Master DB: {args.master_db}")
    logger.info(f"Worker processes: {args.max_workers}")
    
    # Validate inputs
    if not os.path.exists(args.maps_directory):
        logger.error(f"Maps directory {args.maps_directory} does not exist")
        return
    
    if not os.path.exists(args.listfile_path):
        logger.error(f"Listfile {args.listfile_path} does not exist")
        return
    
    # Find map folders
    map_folders = find_map_folders(args.maps_directory)
    logger.info(f"Found {len(map_folders)} map folders")
    
    # Sort by number of ADT files (smallest first for better parallelization)
    map_folders = sorted(map_folders, key=count_adt_files)
    
    if not map_folders:
        logger.error("No map folders found containing ADT files")
        return
    
    # Display found map folders
    for i, folder in enumerate(map_folders):
        adt_count = count_adt_files(folder)
        logger.info(f"Map {i+1}: {folder} ({adt_count} ADT files)")
    
    # Process each map folder
    if not args.skip_individual:
        logger.info("Processing individual map folders")
        
        # Prepare parameters for each map folder
        map_params = []
        db_list = []
        
        for map_folder in map_folders:
            map_name = os.path.basename(map_folder)
            db_path = os.path.join(output_dir, f"{map_name}.db")
            db_list.append(db_path)
            
            # Remove existing database if clean option is set
            if args.clean and os.path.exists(db_path):
                logger.info(f"Removing existing database {db_path}")
                os.remove(db_path)
            
            map_params.append((map_folder, args.listfile_path, db_path, output_dir, args.log_level, args.no_repair))
        
        # Process map folders in parallel
        start_time = time.time()
        with ProcessPoolExecutor(max_workers=args.max_workers) as executor:
            futures = {executor.submit(process_map_folder, params): params[0] for params in map_params}
            
            for future in as_completed(futures):
                map_folder = futures[future]
                try:
                    result = future.result()
                    if result['exit_code'] == 0:
                        logger.info(f"Successfully processed {result['map_folder']}")
                    else:
                        logger.error(f"Error processing {result['map_folder']} (exit code {result['exit_code']})")
                        logger.error(f"STDERR: {result['stderr']}")
                except Exception as e:
                    logger.error(f"Exception processing {map_folder}: {e}")
        
        elapsed_time = time.time() - start_time
        logger.info(f"Processed {len(map_folders)} map folders in {elapsed_time:.2f} seconds")
    
    # Merge databases
    if not args.skip_master:
        # Get the list of databases to merge
        db_list = []
        for map_folder in map_folders:
            map_name = os.path.basename(map_folder)
            db_path = os.path.join(output_dir, f"{map_name}.db")
            if os.path.exists(db_path):
                db_list.append(db_path)
        
        if db_list:
            master_db_path = os.path.join(output_dir, args.master_db)
            # Remove existing master database if clean option is set
            if args.clean and os.path.exists(master_db_path):
                logger.info(f"Removing existing master database {master_db_path}")
                os.remove(master_db_path)
            
            start_time = time.time()
            merge_databases(master_db_path, db_list, logger)
            elapsed_time = time.time() - start_time
            logger.info(f"Merged {len(db_list)} databases in {elapsed_time:.2f} seconds")
        else:
            logger.error("No databases found to merge")
    
    logger.info("Map processing complete")

if __name__ == "__main__":
    main()
