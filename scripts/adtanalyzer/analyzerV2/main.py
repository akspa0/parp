#!/usr/bin/env python3
"""
WoW Terrain Analyzer V2
Command-line interface for analyzing WoW terrain files.
"""
import os
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from modules.parsers import ADTParser, WDTParser
from modules.json import JSONHandler
from modules.database import DatabaseManager
from modules.utils.logging import setup_logging

def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='World of Warcraft Terrain Analyzer V2',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        'path',
        type=Path,
        help='Path to ADT/WDT file or directory'
    )
    
    parser.add_argument(
        '--output',
        type=Path,
        help='Output directory (default: [map_name]_[timestamp])'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of files to process'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=os.cpu_count(),
        help='Maximum number of worker threads'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    return parser.parse_args()

def process_file(
    file_path: Path,
    json_dir: Path,
    logger: logging.Logger
) -> Optional[Path]:
    """Process a single terrain file"""
    try:
        # Determine file type
        file_type = file_path.suffix.lower()[1:]
        if file_type not in ('adt', 'wdt'):
            logger.error(f"Unsupported file type: {file_type}")
            return None
            
        logger.debug(f"Processing {file_type.upper()} file: {file_path}")
        
        # Parse file
        parser = ADTParser(file_path) if file_type == 'adt' else WDTParser(file_path)
        terrain_file = parser.parse()
        
        # Save to JSON
        json_path = JSONHandler.save(terrain_file, json_dir)
        logger.debug(f"Saved to JSON: {json_path}")
        
        return json_path
        
    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}", exc_info=True)
        return None

def process_directory(
    path: Path,
    output_dir: Path,
    max_workers: Optional[int] = None,
    limit: Optional[int] = None,
    logger: Optional[logging.Logger] = None,
    debug: bool = False
) -> None:
    """Process directory of terrain files"""
    # Set up logging if not provided
    if logger is None:
        logger = setup_logging(output_dir, debug)
    
    try:
        # Create json directory
        json_dir = output_dir / 'json'
        json_dir.mkdir(exist_ok=True)
        logger.info(f"JSON output directory: {json_dir}")
        
        # Find terrain files
        adt_files = list(path.glob('*.[aA][dD][tT]'))
        wdt_files = list(path.glob('*.[wW][dD][tT]'))
        
        # Apply limit if specified
        terrain_files = adt_files + wdt_files
        if limit:
            terrain_files = terrain_files[:limit]
            
        total_files = len(terrain_files)
        logger.info(f"Found {len(adt_files)} ADT and {len(wdt_files)} WDT files")
        logger.info(f"Processing {total_files} files...")
        
        if total_files == 0:
            logger.error(f"No terrain files found in {path}")
            return
            
        # Process files in parallel
        processed_files = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all files for processing
            future_to_path = {
                executor.submit(process_file, path, json_dir, logger): path
                for path in terrain_files
            }
            
            # Process results as they complete
            completed = 0
            for future in executor.as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    json_path = future.result()
                    if json_path:
                        processed_files.append(json_path)
                    completed += 1
                    if completed % 100 == 0 or completed == total_files:
                        logger.info(f"Processed {completed}/{total_files} files")
                except Exception as e:
                    logger.error(f"Error processing {path}: {e}", exc_info=True)
        
        logger.info(f"Successfully processed {len(processed_files)} files")
        
        # Build database from JSON files
        if processed_files:
            db_path = output_dir / f"{path.stem}.db"
            logger.info("Building database...")
            db_manager = DatabaseManager(db_path)
            db_manager.build_from_json(json_dir, max_workers, limit)
            logger.info(f"Database saved to: {db_path}")
            
    except Exception as e:
        logger.error(f"Error processing directory: {e}", exc_info=True)
        sys.exit(1)

def main():
    """Main entry point"""
    args = parse_args()
    
    try:
        # Create output directory
        map_name = args.path.stem
        if '_' in map_name:
            map_name = map_name.split('_')[0]
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = args.output or Path(f"{map_name}_{timestamp}")
        output_dir.mkdir(exist_ok=True)
        
        # Set up logging
        logger = setup_logging(output_dir, args.debug)
        logger.info(f"Processing path: {args.path}")
        logger.info(f"Output directory: {output_dir}")
        
        if args.path.is_file():
            # Process single file
            json_dir = output_dir / 'json'
            json_dir.mkdir(exist_ok=True)
            
            json_path = process_file(args.path, json_dir, logger)
            if json_path:
                # Build database
                db_path = output_dir / f"{args.path.stem}.db"
                logger.info("Building database...")
                db_manager = DatabaseManager(db_path)
                db_manager.build_from_json(json_dir, args.workers, args.limit)
                logger.info(f"Database saved to: {db_path}")
                
        elif args.path.is_dir():
            # Process directory
            process_directory(
                args.path,
                output_dir,
                args.workers,
                args.limit,
                logger,
                args.debug
            )
        else:
            logger.error(f"Path not found: {args.path}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()