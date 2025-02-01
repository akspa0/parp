#!/usr/bin/env python3
"""
Universal WoW Map File Decoder
Handles both WDT and ADT files in Alpha and Retail formats
"""

import os
import re
import sys
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Set, Tuple, Dict, Any, Optional

from src.format_detector import FormatDetector, FileFormat, FileType
from src.chunks.registry import ChunkRegistry, ChunkFormat
from src.output import JSONOutputHandler, SQLiteOutputHandler

def setup_logging(output_dir: str) -> Tuple[logging.Logger, str]:
    """Setup logging configuration"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path(output_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"decoder_{timestamp}.log"
    missing_log = log_dir / f"missing_files_{timestamp}.log"
    
    # Configure main logger
    logging.basicConfig(
        filename=str(log_file),
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure missing files logger
    missing_logger = logging.getLogger('missing_files')
    missing_handler = logging.FileHandler(missing_log)
    missing_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    missing_logger.addHandler(missing_handler)
    missing_logger.setLevel(logging.INFO)
    
    # Add console handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    
    return logging.getLogger(__name__), str(log_file)

def process_embedded_adt(data: bytes, offset: int, size: int, format_type: FileFormat, reversed_chunks: bool) -> Dict[str, Any]:
    """Process ADT data embedded within WDT file"""
    logger = logging.getLogger(__name__)
    chunk_registry = ChunkRegistry()
    chunk_format = ChunkFormat.ALPHA if format_type == FileFormat.ALPHA else ChunkFormat.RETAIL
    
    decoded_data = {}
    errors = []
    
    # Extract ADT data
    adt_data = data[offset:offset + size]
    pos = 0
    
    while pos < len(adt_data):
        if pos + 8 > len(adt_data):
            break
            
        # Read chunk header
        chunk_name = adt_data[pos:pos+4]
        if reversed_chunks:
            chunk_name = chunk_name[::-1]
            
        chunk_size = int.from_bytes(adt_data[pos+4:pos+8], 'little')
        
        if pos + 8 + chunk_size > len(adt_data):
            errors.append(f"Chunk {chunk_name} extends beyond ADT data size")
            break
            
        # Get decoder for this chunk
        decoder = chunk_registry.get_decoder(chunk_name, chunk_format)
        
        chunk_name_str = chunk_name.decode('ascii')
        logger.debug(f"Processing embedded ADT chunk: {chunk_name_str} at offset {pos}, size {chunk_size}")
        
        if decoder:
            try:
                chunk_data = adt_data[pos+8:pos+8+chunk_size]
                result = decoder.decode(chunk_data)
                
                # Store decoded data
                if chunk_name_str not in decoded_data:
                    decoded_data[chunk_name_str] = []
                decoded_data[chunk_name_str].append(result)
                
                logger.debug(f"Decoded {chunk_name_str}: {result}")
                
            except Exception as e:
                error_msg = f"Error decoding {chunk_name_str}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        else:
            # Store raw chunk data for unknown chunks
            if 'raw_chunks' not in decoded_data:
                decoded_data['raw_chunks'] = {}
            decoded_data['raw_chunks'][chunk_name_str] = {
                'offset': pos,
                'size': chunk_size,
                'data': adt_data[pos+8:pos+8+chunk_size].hex()[:100] + '...'
            }
            logger.debug(f"Unknown chunk {chunk_name_str} stored as raw data")
        
        pos += 8 + chunk_size
    
    if errors:
        decoded_data['errors'] = errors
        
    return decoded_data

def process_wdt_file(file_path: str, format_type: FileFormat, reversed_chunks: bool) -> Dict[str, Any]:
    """Process WDT file and its embedded ADT data"""
    logger = logging.getLogger(__name__)
    chunk_registry = ChunkRegistry()
    chunk_format = ChunkFormat.ALPHA if format_type == FileFormat.ALPHA else ChunkFormat.RETAIL
    
    decoded_data = {}
    errors = []
    
    with open(file_path, 'rb') as f:
        data = f.read()
        pos = 0
        
        while pos < len(data):
            if pos + 8 > len(data):
                break
                
            # Read chunk header
            chunk_name = data[pos:pos+4]
            if reversed_chunks:
                chunk_name = chunk_name[::-1]
                
            chunk_size = int.from_bytes(data[pos+4:pos+8], 'little')
            
            if pos + 8 + chunk_size > len(data):
                errors.append(f"Chunk {chunk_name} extends beyond file size")
                break
                
            # Get decoder for this chunk
            decoder = chunk_registry.get_decoder(chunk_name, chunk_format)
            
            chunk_name_str = chunk_name.decode('ascii')
            logger.debug(f"Processing chunk: {chunk_name_str} at offset {pos}, size {chunk_size}")
            
            if decoder:
                try:
                    chunk_data = data[pos+8:pos+8+chunk_size]
                    result = decoder.decode(chunk_data)
                    
                    # Store decoded data
                    if chunk_name_str not in decoded_data:
                        decoded_data[chunk_name_str] = []
                    decoded_data[chunk_name_str].append(result)
                    
                    # For MAIN chunk in Alpha format, process embedded ADT data
                    if chunk_name_str == 'MAIN' and format_type == FileFormat.ALPHA:
                        main_data = result
                        adt_data = {}
                        
                        for y, row in enumerate(main_data.get('tiles', [])):
                            for x, tile in enumerate(row):
                                if tile['has_data'] and tile['offset'] > 0:
                                    logger.info(f"Processing embedded ADT at ({x}, {y})")
                                    adt_name = f"{Path(file_path).stem}_{x}_{y}.adt"
                                    adt_data[adt_name] = process_embedded_adt(
                                        data,
                                        tile['offset'],
                                        tile['size'],
                                        format_type,
                                        reversed_chunks
                                    )
                        
                        decoded_data['adt_files'] = adt_data
                    
                    logger.debug(f"Decoded {chunk_name_str}: {result}")
                    
                except Exception as e:
                    error_msg = f"Error decoding {chunk_name_str}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            else:
                # Store raw chunk data for unknown chunks
                if 'raw_chunks' not in decoded_data:
                    decoded_data['raw_chunks'] = {}
                decoded_data['raw_chunks'][chunk_name_str] = {
                    'offset': pos,
                    'size': chunk_size,
                    'data': data[pos+8:pos+8+chunk_size].hex()[:100] + '...'
                }
                logger.debug(f"Unknown chunk {chunk_name_str} stored as raw data")
            
            pos += 8 + chunk_size
    
    if errors:
        decoded_data['errors'] = errors
        
    return decoded_data

def process_adt_file(file_path: str, format_type: FileFormat, reversed_chunks: bool) -> Dict[str, Any]:
    """Process a single ADT file"""
    logger = logging.getLogger(__name__)
    chunk_registry = ChunkRegistry()
    chunk_format = ChunkFormat.ALPHA if format_type == FileFormat.ALPHA else ChunkFormat.RETAIL
    
    decoded_data = {}
    errors = []
    
    with open(file_path, 'rb') as f:
        data = f.read()
        pos = 0
        
        while pos < len(data):
            if pos + 8 > len(data):
                break
                
            # Read chunk header
            chunk_name = data[pos:pos+4]
            if reversed_chunks:
                chunk_name = chunk_name[::-1]
                
            chunk_size = int.from_bytes(data[pos+4:pos+8], 'little')
            
            if pos + 8 + chunk_size > len(data):
                errors.append(f"Chunk {chunk_name} extends beyond file size")
                break
                
            # Get decoder for this chunk
            decoder = chunk_registry.get_decoder(chunk_name, chunk_format)
            
            chunk_name_str = chunk_name.decode('ascii')
            logger.debug(f"Processing chunk: {chunk_name_str} at offset {pos}, size {chunk_size}")
            
            if decoder:
                try:
                    chunk_data = data[pos+8:pos+8+chunk_size]
                    result = decoder.decode(chunk_data)
                    
                    # Store decoded data
                    if chunk_name_str not in decoded_data:
                        decoded_data[chunk_name_str] = []
                    decoded_data[chunk_name_str].append(result)
                    
                    logger.debug(f"Decoded {chunk_name_str}: {result}")
                    
                except Exception as e:
                    error_msg = f"Error decoding {chunk_name_str}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            else:
                # Store raw chunk data for unknown chunks
                if 'raw_chunks' not in decoded_data:
                    decoded_data['raw_chunks'] = {}
                decoded_data['raw_chunks'][chunk_name_str] = {
                    'offset': pos,
                    'size': chunk_size,
                    'data': data[pos+8:pos+8+chunk_size].hex()[:100] + '...'
                }
                logger.debug(f"Unknown chunk {chunk_name_str} stored as raw data")
            
            pos += 8 + chunk_size
    
    if errors:
        decoded_data['errors'] = errors
        
    return decoded_data

def process_file(file_path: str, output_dir: str, map_name: Optional[str] = None, listfile_path: Optional[str] = None) -> bool:
    """Process a single file (WDT or ADT)"""
    try:
        # Initialize handlers
        json_handler = JSONOutputHandler(output_dir)
        sqlite_handler = SQLiteOutputHandler(output_dir)
        logger = logging.getLogger(__name__)
        
        # Detect file format
        detector = FormatDetector(file_path)
        file_type, format_type, reversed_chunks = detector.detect_format()
        
        logger.info(f"\nProcessing {file_path}")
        logger.info(f"Type: {file_type.name}")
        logger.info(f"Format: {format_type.name}")
        logger.info(f"Reversed chunks: {reversed_chunks}")
        
        if file_type == FileType.WDT:
            # Process WDT and embedded ADTs
            decoded_data = process_wdt_file(file_path, format_type, reversed_chunks)
            
            # Write outputs
            json_path = json_handler.write_wdt_data(file_path, format_type.name, decoded_data)
            db_path = sqlite_handler.write_wdt_data(file_path, format_type.name, decoded_data)
            
            logger.info(f"JSON output written to: {json_path}")
            logger.info(f"SQLite output written to: {db_path}")
            return True
        else:
            # Process single ADT file
            decoded_data = process_adt_file(file_path, format_type, reversed_chunks)
            
            # Write outputs
            json_path = json_handler.write_adt_data(file_path, format_type.name, decoded_data)
            db_path = sqlite_handler.write_adt_data(file_path, format_type.name, decoded_data, map_name)
            
            logger.info(f"JSON output written to: {json_path}")
            logger.info(f"SQLite output written to: {db_path}")
            return True
            
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return False

def process_directory(directory: str,
                     output_dir: str,
                     listfile_path: Optional[str] = None,
                     pattern: str = "*.{adt,wdt}") -> Tuple[int, int]:
    """Process all WDT and ADT files in a directory"""
    path = Path(directory)
    files = list(path.rglob(pattern))
    total = len(files)
    
    if total == 0:
        logging.warning(f"No matching files found in {directory}")
        return 0, 0
    
    logging.info(f"\nProcessing {total} files from {directory}")
    
    successful = 0
    failed = 0
    
    # Extract map name from directory name
    map_name = path.name
    
    # Sort files to process WDT first if it exists
    wdt_files = [f for f in files if f.suffix.lower() == '.wdt']
    adt_files = [f for f in files if f.suffix.lower() == '.adt']
    
    # Process WDT first if it exists
    for file_path in wdt_files:
        logging.info(f"\nProcessing WDT file: {file_path.name}")
        if process_file(str(file_path), output_dir, listfile_path=listfile_path):
            successful += 1
        else:
            failed += 1
    
    # Then process ADT files
    adt_pattern = re.compile(r'^(?:.*?)(\d+)_(\d+)\.adt$', re.IGNORECASE)
    for file_path in adt_files:
        match = adt_pattern.search(file_path.name)
        if not match:
            logging.warning(f"Skipping {file_path.name}, does not match pattern _X_Y.adt")
            continue
            
        logging.info(f"\nProcessing ADT file: {file_path.name}")
        if process_file(str(file_path), output_dir, map_name, listfile_path):
            successful += 1
        else:
            failed += 1
            
        logging.info(f"Progress: {successful + failed}/{total} files processed")
    
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
    logger, log_file = setup_logging(args.output_dir)
    
    try:
        if os.path.isfile(args.input):
            # Process single file
            success = process_file(args.input, args.output_dir, listfile_path=args.listfile)
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
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()