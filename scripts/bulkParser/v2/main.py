#!/usr/bin/env python3
"""
ADT Analyzer - Main Entry Point
Parses ADT files and extracts detailed information into a database
Supports classic and split ADT formats with FileDataID resolution
"""

import os
import sys
import logging
import argparse
from datetime import datetime

# Import local modules
from utils import setup_logging, write_uid_file, generate_patch_file
from database import setup_database 
from adt_parser import parse_directory, load_listfile

def main():
    """Main entry point for the ADT analyzer"""
    parser = argparse.ArgumentParser(description="World of Warcraft ADT file analyzer")
    parser.add_argument("directory", help="Directory containing ADT files to analyze")
    parser.add_argument("listfile", help="Path to listfile for file reference checks")
    parser.add_argument("--db", dest="database", default="analysis.db", 
                        help="Path to database file (default: analysis.db)")
    parser.add_argument("--log-dir", dest="log_dir", default=None,
                        help="Directory for log files (default: same directory as database)")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
                        default="INFO", help="Set the logging level")
    parser.add_argument("--no-repair", action="store_true", 
                        help="Disable automatic file path repair attempts")
    
    args = parser.parse_args()
    
    # Generate timestamp for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Setup log directory
    if args.log_dir:
        log_dir = args.log_dir
    else:
        log_dir = os.path.join(os.path.dirname(args.database), "logs")
    
    os.makedirs(log_dir, exist_ok=True)
    
    # Setup logging
    loggers = setup_logging(log_dir, timestamp, args.log_level)
    logger = loggers["parser"]
    missing_logger = loggers["missing"]
    
    logger.info(f"Starting analysis of ADT files in {args.directory}")
    
    # Set up the database
    conn = setup_database(args.database)
    
    # Make sure the database directory exists
    db_dir = os.path.dirname(args.database)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    # Load the listfile
    known_good_files, file_data_id_map = load_listfile(args.listfile, logger)
    
    # Parse the directory
    all_unique_ids, repairs = parse_directory(
        args.directory, 
        conn, 
        known_good_files, 
        file_data_id_map, 
        loggers,
        attempt_repairs=not args.no_repair
    )
    
    # Check uniqueID uniqueness
    if len(all_unique_ids) != len(set(all_unique_ids)):
        logger.warning("Not all uniqueIDs are unique! This violates the specification.")

    # Store max uniqueID in uid.ini
    if all_unique_ids:
        max_uid = max(all_unique_ids)
        write_uid_file(args.directory, max_uid)
        logger.info(f"Maximum uniqueID in {args.directory} is {max_uid}. Written to uid.ini.")
    else:
        logger.warning("No uniqueIDs found in any ADT files!")

    # Generate repair file if repairs were found
    if repairs:
        patch_path = generate_patch_file(args.directory, repairs, timestamp)
        logger.info(f"Generated path patch file at {patch_path}")

    conn.close()
    logger.info("Analysis complete.")

if __name__ == "__main__":
    main()
