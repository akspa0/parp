#!/usr/bin/env python3
"""
Universal WoW Map File Decoder
Handles both WDT and ADT files in Alpha and Retail formats
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple, Set

from .format_detector import FormatDetector, FileType, FileFormat
from .base.chunk_parser import ChunkParsingError
from .database.operations import DatabaseOperations
from .formats.alpha.wdt_parser import AlphaWDTParser
from .formats.alpha.adt_parser import AlphaADTParser
from .formats.retail.wdt_parser import RetailWDTParser
from .formats.retail.adt_parser import RetailADTParser

def setup_logging(output_dir: str) -> Tuple[logging.Logger, str, logging.Logger]:
    """Setup logging configuration"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path(output_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Main log file
    log_file = log_dir / f"decoder_{timestamp}.log"
    
    # Configure file logging
    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Add console handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    
    # Setup missing files logger
    missing_logger = logging.getLogger('missing_files')
    missing_file_handler = logging.FileHandler(log_dir / f"missing_files_{timestamp}.log")
    missing_file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    missing_logger.addHandler(missing_file_handler)
    missing_logger.setLevel(logging.INFO)
    
    return logging.getLogger(__name__), str(log_file), missing_logger

def load_listfile(listfile_path: str) -> Set[str]:
    """Load and normalize listfile entries"""
    known_files = set()
    if os.path.exists(listfile_path):
        with open(listfile_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if ';' in line:
                    filename = line.split(';')[1].strip().lower()
                    if filename.endswith('.mdx'):
                        filename = filename[:-4] + '.m2'
                    known_files.add(filename)
        logging.info(f"Loaded {len(known_files)} known files from {listfile_path}")
    else:
        logging.warning(f"Listfile not found: {listfile_path}")
    return known_files

def process_file(file_path: str,
                output_dir: str,
                db_ops: DatabaseOperations,
                known_files: Optional[Set[str]] = None) -> bool:
    """
    Process a single WDT or ADT file
    
    Args:
        file_path: Path to the file to process
        output_dir: Directory for output files
        db_ops: Database operations instance
        known_files: Set of known good files for validation
        
    Returns:
        bool: Whether processing was successful
    """
    try:
        # Detect file format
        detector = FormatDetector(file_path)
        file_type, format_type, reversed_chunks = detector.detect_format()
        
        logging.info(f"\nProcessing {file_path}")
        logging.info(f"Type: {file_type.name}")
        logging.info(f"Format: {format_type.name}")
        logging.info(f"Reversed chunks: {reversed_chunks}")
        
        try:
            # Select appropriate parser
            if file_type == FileType.WDT:
                if format_type == FileFormat.ALPHA:
                    parser = AlphaWDTParser(file_path, reversed_chunks)
                else:
                    parser = RetailWDTParser(file_path, reversed_chunks)
            else:  # ADT
                if format_type == FileFormat.ALPHA:
                    parser = AlphaADTParser(file_path, reversed_chunks)
                else:
                    parser = RetailADTParser(file_path, reversed_chunks)
            
            # Parse file
            with parser:
                if not parser.validate():
                    logging.error("File validation failed")
                    return False
                
                result = parser.parse()
                logging.info("Parsing completed successfully")
                
                # Store in database
                if file_type == FileType.WDT:
                    map_id = db_ops.process_wdt_data(
                        file_path,
                        format_type.name,
                        result
                    )
                else:  # ADT
                    # Extract map name and coordinates from ADT filename
                    path = Path(file_path)
                    parts = path.stem.split('_')
                    if len(parts) >= 3:
                        map_name = '_'.join(parts[:-2])
                        x, y = int(parts[-2]), int(parts[-1])
                        
                        # Find or create map record
                        cursor = db_ops.db.conn.execute(
                            "SELECT id FROM maps WHERE name = ?",
                            (map_name,)
                        )
                        row = cursor.fetchone()
                        if row:
                            map_id = row[0]
                        else:
                            map_id = db_ops.insert_map(
                                map_name,
                                format_type.name,
                                result.get('version', 0),
                                result.get('flags', 0)
                            )
                        
                        # Create tile record
                        tile_id = db_ops.insert_map_tile(
                            map_id, x, y,
                            result.get('flags', 0),
                            True,  # has_data
                            path.name
                        )
                        
                        # Process ADT data
                        db_ops.process_adt_data(map_id, tile_id, result)
                    else:
                        logging.error(f"Invalid ADT filename format: {file_path}")
                        return False
            
            return True
            
        except ChunkParsingError as e:
            logging.error(f"Chunk parsing error: {e}")
            return False
            
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        return False

def process_directory(directory: str,
                     output_dir: str,
                     listfile_path: Optional[str] = None,
                     pattern: str = "*.{adt,wdt}") -> Tuple[int, int]:
    """
    Process all WDT and ADT files in a directory
    
    Args:
        directory: Directory containing files to process
        output_dir: Directory for output files
        listfile_path: Optional path to listfile for validation
        pattern: Glob pattern for matching files
        
    Returns:
        Tuple of (successful_count, failed_count)
    """
    path = Path(directory)
    files = list(path.rglob(pattern))
    total = len(files)
    
    if total == 0:
        logging.warning(f"No matching files found in {directory}")
        return 0, 0
    
    logging.info(f"\nProcessing {total} files from {directory}")
    
    # Setup database
    db_path = os.path.join(output_dir, "map_data.db")
    db_ops = DatabaseOperations(db_path)
    
    # Load listfile if provided
    known_files = load_listfile(listfile_path) if listfile_path else None
    
    successful = 0
    failed = 0
    
    try:
        for i, file_path in enumerate(files, 1):
            logging.info(f"\nProcessing file {i}/{total}: {file_path.name}")
            
            if process_file(str(file_path), output_dir, db_ops, known_files):
                successful += 1
            else:
                failed += 1
                
            logging.info(f"Progress: {i}/{total} files processed")
        
        # Generate uid.ini if we have unique IDs
        if db_ops.unique_ids:
            db_ops.write_uid_ini(output_dir)
            logging.info(f"Generated uid.ini with max ID: {max(db_ops.unique_ids)}")
            
    finally:
        db_ops.close()
    
    return successful, failed

def main():
    parser = argparse.ArgumentParser(
        description="Universal WoW Map File Decoder - Handles both WDT and ADT files"
    )
    
    parser.add_argument(
        'input',
        help="File or directory to process"
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        default='output',
        help="Output directory (default: output)"
    )
    
    parser.add_argument(
        '-l', '--listfile',
        help="Path to listfile for validation"
    )
    
    parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        help="Process directories recursively"
    )
    
    args = parser.parse_args()
    
    # Setup output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Setup logging
    logger, log_file, missing_logger = setup_logging(args.output_dir)
    
    try:
        if os.path.isfile(args.input):
            # Process single file
            db_ops = DatabaseOperations(os.path.join(args.output_dir, "map_data.db"))
            known_files = load_listfile(args.listfile) if args.listfile else None
            
            try:
                success = process_file(args.input, args.output_dir, db_ops, known_files)
                if db_ops.unique_ids:
                    db_ops.write_uid_ini(args.output_dir)
                sys.exit(0 if success else 1)
            finally:
                db_ops.close()
                
        elif os.path.isdir(args.input):
            # Process directory
            successful, failed = process_directory(
                args.input,
                args.output_dir,
                args.listfile,
                "**/*.{adt,wdt}" if args.recursive else "*.{adt,wdt}"
            )
            
            logger.info("\nProcessing complete!")
            logger.info(f"Successful: {successful}")
            logger.info(f"Failed: {failed}")
            logger.info(f"Log file: {log_file}")
            
            sys.exit(1 if failed > 0 else 0)
        else:
            logger.error(f"Input path does not exist: {args.input}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\nProcessing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()