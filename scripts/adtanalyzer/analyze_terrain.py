#!/usr/bin/env python3
"""
World of Warcraft Terrain Analyzer
Supports both ADT and WDT files in Retail and Alpha formats.
"""
import os
import re
import sys
import json
import logging
import argparse
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from terrain_structures import TerrainFile, ADTFile, WDTFile
from adt_parser import ADTParser
from wdt_parser import WDTParser
from json_handler import save_to_json
from db_builder import build_database
from terrain_database import setup_database

def setup_logging(output_dir: Path, debug: bool = False) -> Tuple[logging.Logger, logging.Logger]:
    """Set up logging"""
    # Main logger
    logger = logging.getLogger('terrain_analyzer')
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create logs directory
    logs_dir = output_dir / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    # File handler
    log_path = logs_dir / 'terrain_parser.log'
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.addHandler(console_handler)
    
    # Missing files logger
    missing_logger = logging.getLogger('missing_files')
    missing_logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    missing_logger.handlers.clear()
    
    missing_log_path = logs_dir / 'missing_files.log'
    missing_handler = logging.FileHandler(missing_log_path)
    missing_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    missing_logger.addHandler(missing_handler)
    
    return logger, missing_logger

def write_visualization(grid: List[List[int]], output_path: Path):
    """Write text-based visualization of the terrain grid"""
    visualization = "\n".join(
        "".join("#" if cell else "." for cell in row)
        for row in grid
    )
    
    with open(output_path, 'w') as f:
        f.write("Terrain Grid Visualization:\n")
        f.write("# = Active tile/chunk\n")
        f.write(". = Empty tile/chunk\n\n")
        f.write(visualization)
        f.write("\n")

def normalize_filename(fname: str) -> str:
    """Normalize file path"""
    if not fname or fname == "<invalid offset>":
        return ""
    
    fname = fname.lower().replace('\\', '/')
    fname = fname.lstrip('./').lstrip('/')
    
    if fname.endswith('.mdx'):
        fname = fname[:-4] + '.m2'
    
    return fname

def load_listfile(listfile_path: Path, logger: logging.Logger) -> Set[str]:
    """Load known file list"""
    known_files = set()
    
    if not listfile_path.exists():
        logger.warning(f"Listfile not found: {listfile_path}")
        return known_files
        
    try:
        with open(listfile_path, 'r', encoding='utf-8') as f:
            for line in f:
                if ';' in line:
                    _, filename = line.strip().split(';', 1)
                    norm = normalize_filename(filename)
                    if norm:
                        known_files.add(norm)
                        
        logger.info(f"Loaded {len(known_files)} known files")
        
    except Exception as e:
        logger.error(f"Error loading listfile: {e}")
        logger.debug(traceback.format_exc())
        
    return known_files

def process_terrain_file(file_path: Path, output_dir: Path,
                        logger: logging.Logger) -> Optional[Path]:
    """
    Process terrain file to JSON
    
    Args:
        file_path: Path to ADT/WDT file
        output_dir: Directory for JSON output
        logger: Logger instance
        
    Returns:
        Path to JSON file if successful, None otherwise
    """
    try:
        # Determine file type
        file_type = file_path.suffix.lower()[1:]  # Remove dot
        if file_type not in ('adt', 'wdt'):
            logger.error(f"Unsupported file type: {file_type}")
            return None
            
        logger.debug(f"Processing {file_type.upper()} file: {file_path}")
        
        # Parse file
        parser = ADTParser(str(file_path)) if file_type == 'adt' else WDTParser(str(file_path))
        terrain_file = parser.parse()
        
        # Save to JSON
        json_path = save_to_json(terrain_file, output_dir)
        logger.debug(f"Saved to JSON: {json_path}")
        
        # Create visualization for WDT files
        if isinstance(terrain_file, WDTFile):
            grid = [[0] * 64 for _ in range(64)]
            for tile in terrain_file.tiles.values():
                grid[tile.y][tile.x] = 1
            vis_path = file_path.with_suffix('.vis.txt')
            write_visualization(grid, vis_path)
            logger.debug(f"Grid visualization saved to: {vis_path}")
            
        return json_path
        
    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        logger.debug(traceback.format_exc())
        return None

def process_directory(path: Path, listfile_path: Optional[Path],
                     output_dir: Path, max_workers: Optional[int] = None,
                     logger: Optional[logging.Logger] = None,
                     debug: bool = False, limit: Optional[int] = None):
    """
    Process directory of terrain files
    
    Args:
        path: Directory containing ADT/WDT files
        listfile_path: Optional path to listfile
        db_path: Path to output database
        max_workers: Maximum number of worker threads
        logger: Optional logger instance
        debug: Enable debug logging
    """
    # Extract map name and create output directory
    map_name = path.stem
    if '_' in map_name:
        map_name = map_name.split('_')[0]  # Get base map name before any coordinates
        
    # Create timestamped output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"{map_name}_{timestamp}")
    output_dir.mkdir(exist_ok=True)
    
    if logger is None:
        logger, _ = setup_logging(output_dir, debug)
    
    try:
        # Create json subdirectory
        json_dir = output_dir / 'json'
        json_dir.mkdir(exist_ok=True)
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"JSON output directory: {json_dir}")
        
        # Find all terrain files
        adt_files = list(path.glob('*.[aA][dD][tT]'))
        wdt_files = list(path.glob('*.[wW][dD][tT]'))
        total_files = len(adt_files) + len(wdt_files)
        
        logger.info(f"Found {len(adt_files)} ADT files and {len(wdt_files)} WDT files")
        
        if total_files == 0:
            logger.error(f"No terrain files found in {path}")
            return
        
        # Process files in parallel
        processed_files = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all files for processing
            future_to_path = {
                executor.submit(process_terrain_file, path, json_dir, logger): path
                for path in adt_files + wdt_files
            }
            
            # Process results as they complete
            completed = 0
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    json_path = future.result()
                    if json_path:
                        processed_files.append(json_path)
                    completed += 1
                    if completed % 100 == 0 or completed == total_files:
                        logger.info(f"Processed {completed}/{total_files} files to JSON")
                except Exception as e:
                    logger.error(f"Error processing {path}: {e}")
                    logger.debug(traceback.format_exc())
        
        logger.info(f"Successfully processed {len(processed_files)} files to JSON")
        
        if processed_files:
            # Process WDT files first
            wdt_jsons = [f for f in processed_files if f.stem.endswith('.wdt')]
            if wdt_jsons:
                wdt_db_path = output_dir / f"{map_name}.wdt.db"
                logger.info("Building WDT database...")
                build_database(json_dir, wdt_db_path, max_workers, limit)
                logger.info(f"WDT Database: {wdt_db_path}")
            
            # Process ADT files
            adt_jsons = [f for f in processed_files if not f.stem.endswith('.wdt')]
            for json_file in adt_jsons:
                # Extract tile coordinates from filename
                tile_coords = json_file.stem.split('_')[-2:]
                if len(tile_coords) == 2:
                    adt_db_path = output_dir / f"{json_file.stem}.db"
                    logger.info(f"Building database for tile {json_file.stem}...")
                    # Create a temporary directory for this tile's JSON
                    tile_json_dir = output_dir / 'temp_json' / json_file.stem
                    tile_json_dir.mkdir(parents=True, exist_ok=True)
                    # Copy just this tile's JSON to the temp directory
                    import shutil
                    shutil.copy2(json_file, tile_json_dir / json_file.name)
                    # Build database using only this tile's JSON
                    build_database(tile_json_dir, adt_db_path, max_workers, limit)
                    # Clean up temp directory
                    shutil.rmtree(tile_json_dir.parent)
                    logger.info(f"Tile Database: {adt_db_path}")
                else:
                    logger.warning(f"Invalid ADT filename format: {json_file}")
            
            logger.info("Processing complete")
            logger.info(f"JSON files: {json_dir}")
        else:
            logger.error("No files were successfully processed")
            
    except Exception as e:
        logger.error(f"Error processing directory: {e}")
        logger.debug(traceback.format_exc())
        sys.exit(1)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='World of Warcraft Terrain Analyzer')
    parser.add_argument('path', help='Path to ADT/WDT file or directory')
    parser.add_argument('--listfile', help='Path to listfile for checking references')
    parser.add_argument('--db', help='Output database path', default='terrain_analysis.db')
    parser.add_argument('--workers', type=int, help='Maximum number of worker threads')
    parser.add_argument('--limit', type=int, help='Maximum number of files to process')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    
    try:
        path = Path(args.path)
        listfile_path = Path(args.listfile) if args.listfile else None
        
        # Extract map name and create output directory
        map_name = path.stem
        if '_' in map_name:
            map_name = map_name.split('_')[0]  # Get base map name before any coordinates
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(f"{map_name}_{timestamp}")
        output_dir.mkdir(exist_ok=True)
        
        # Set up logging in output directory
        logger, missing_logger = setup_logging(output_dir, args.debug)
        
        # Set database path in output directory if not specified
        db_path = output_dir / f"{map_name}.db" if not args.db else Path(args.db)
        
        logger.info(f"Processing path: {path}")
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"Database path: {db_path}")
        if listfile_path:
            logger.info(f"Listfile path: {listfile_path}")
        
        if path.is_file():
            # Process single file
            json_dir = output_dir / 'json'
            json_dir.mkdir(exist_ok=True)
            
            # Determine database path based on file type
            if path.suffix.lower() == '.wdt':
                db_path = output_dir / f"{path.stem}.wdt.db"
            else:
                # For ADT files, use tile coordinates in db name
                tile_coords = path.stem.split('_')[-2:]  # Get last two parts for coordinates
                if len(tile_coords) == 2:
                    db_path = output_dir / f"{path.stem}.db"
                else:
                    logger.error(f"Invalid ADT filename format: {path}")
                    return
            
            json_path = process_terrain_file(path, json_dir, logger)
            if json_path:
                logger.info("Building database...")
                # Create a temporary directory for this file's JSON
                temp_json_dir = output_dir / 'temp_json' / path.stem
                temp_json_dir.mkdir(parents=True, exist_ok=True)
                # Copy just this file's JSON to the temp directory
                import shutil
                shutil.copy2(json_path, temp_json_dir / json_path.name)
                # Build database using only this file's JSON
                build_database(temp_json_dir, db_path, args.workers, args.limit)
                # Clean up temp directory
                shutil.rmtree(temp_json_dir.parent)
                
        elif path.is_dir():
            # Process directory
            process_directory(path, listfile_path, output_dir, args.workers, logger, args.debug, args.limit)
        else:
            logger.error(f"Path not found: {path}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.debug(traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    main()