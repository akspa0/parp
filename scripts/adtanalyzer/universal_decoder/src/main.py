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
from typing import Optional, List, Tuple

from .format_detector import FormatDetector, FileType, FileFormat
from .base.chunk_parser import ChunkParsingError
from .database.models import setup_database
from .formats.alpha.wdt_parser import AlphaWDTParser
from .formats.alpha.adt_parser import AlphaADTParser
from .formats.retail.wdt_parser import RetailWDTParser
from .formats.retail.adt_parser import RetailADTParser

def setup_logging(output_dir: str) -> Tuple[logging.Logger, str]:
    """Setup logging configuration"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path(output_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
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
    
    return logging.getLogger(__name__), str(log_file)

def process_file(file_path: str,
                output_dir: str,
                listfile_path: Optional[str] = None) -> bool:
    """
    Process a single WDT or ADT file
    
    Args:
        file_path: Path to the file to process
        output_dir: Directory for output files
        listfile_path: Optional path to listfile for validation
        
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
        
        # Setup database
        db_path = os.path.join(output_dir, "map_data.db")
        conn = setup_database(db_path)
        
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
                
                # Additional validation if listfile provided
                if listfile_path and os.path.exists(listfile_path):
                    validate_against_listfile(result, listfile_path)
            
            return True
            
        finally:
            conn.close()
            
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
    
    successful = 0
    failed = 0
    
    for i, file_path in enumerate(files, 1):
        logging.info(f"\nProcessing file {i}/{total}: {file_path.name}")
        
        if process_file(str(file_path), output_dir, listfile_path):
            successful += 1
        else:
            failed += 1
            
        logging.info(f"Progress: {i}/{total} files processed")
    
    return successful, failed

def validate_against_listfile(parse_result: dict, listfile_path: str) -> None:
    """Validate parsed data against known-good listfile"""
    with open(listfile_path, 'r', encoding='utf-8') as f:
        known_files = {line.strip().split(';')[1].lower() for line in f if ';' in line}
    
    # Check M2 models
    for model in parse_result.get('m2_models', []):
        if model.lower() not in known_files:
            logging.warning(f"Unknown M2 model: {model}")
    
    # Check WMO models
    for model in parse_result.get('wmo_models', []):
        if model.lower() not in known_files:
            logging.warning(f"Unknown WMO model: {model}")
    
    # Check textures
    for texture in parse_result.get('textures', []):
        if texture.lower() not in known_files:
            logging.warning(f"Unknown texture: {texture}")

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
    logger, log_file = setup_logging(args.output_dir)
    
    try:
        if os.path.isfile(args.input):
            # Process single file
            success = process_file(args.input, args.output_dir, args.listfile)
            sys.exit(0 if success else 1)
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