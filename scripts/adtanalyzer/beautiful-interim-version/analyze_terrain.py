#!/usr/bin/env python3
"""
World of Warcraft Terrain Analyzer
Supports both ADT and WDT files in Retail and Alpha formats.
"""
import os
import sys
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set, Tuple

from terrain_structures import TerrainFile, ADTFile, WDTFile
from terrain_database import setup_database
from adt_parser import ADTParser
from wdt_parser import WDTParser

def setup_logging(timestamp: str) -> Tuple[logging.Logger, logging.Logger]:
    """Set up logging"""
    # Main logger
    logger = logging.getLogger('terrain_analyzer')
    logger.setLevel(logging.DEBUG)
    
    file_handler = logging.FileHandler(f"terrain_parser_{timestamp}.log")
    file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    
    # Missing files logger
    missing_logger = logging.getLogger('missing_files')
    missing_logger.setLevel(logging.INFO)
    missing_handler = logging.FileHandler(f"missing_files_{timestamp}.log")
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
        
    with open(listfile_path, 'r', encoding='utf-8') as f:
        for line in f:
            if ';' in line:
                _, filename = line.strip().split(';', 1)
                norm = normalize_filename(filename)
                if norm:
                    known_files.add(norm)
                    
    logger.info(f"Loaded {len(known_files)} known files")
    return known_files

def process_terrain_file(file_path: Path, listfile_path: Optional[Path], db_path: Path,
                        logger: logging.Logger, missing_logger: logging.Logger):
    """Process terrain file (ADT or WDT)"""
    # Determine file type
    file_type = file_path.suffix.lower()[1:]  # Remove dot
    if file_type not in ('adt', 'wdt'):
        logger.error(f"Unsupported file type: {file_type}")
        return
        
    logger.info(f"\nProcessing {file_type.upper()} file: {file_path}")
    logger.info("=" * 50)
    
    # Parse file
    try:
        parser = ADTParser(str(file_path)) if file_type == 'adt' else WDTParser(str(file_path))
        terrain_file = parser.parse()
        
        # Set up database
        conn = setup_database(db_path)
        
        # Load listfile if provided
        known_files = load_listfile(listfile_path, logger) if listfile_path else set()
        
        try:
            # Store file info
            c = conn.cursor()
            
            # Insert terrain file record
            c.execute("""
                INSERT INTO terrain_files
                (filename, file_type, format_type, map_name, version, flags, chunk_order)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                str(file_path),
                terrain_file.file_type,
                terrain_file.format_type,
                terrain_file.map_name,
                terrain_file.version,
                int(terrain_file.flags),
                ','.join(terrain_file.chunk_order)
            ))
            file_id = c.lastrowid
            
            # Process based on file type
            if isinstance(terrain_file, ADTFile):
                # Store textures
                for tex in terrain_file.textures:
                    c.execute("""
                        INSERT INTO textures
                        (file_id, tile_x, tile_y, filename, flags, effect_id)
                        VALUES (?, -1, -1, ?, ?, ?)
                    """, (file_id, tex.filename, tex.flags, tex.effect_id))
                    
                    if known_files:
                        norm = normalize_filename(tex.filename)
                        if norm and norm not in known_files:
                            missing_logger.info(f"Missing texture: {tex.filename}")
                
                # Store models
                for model in terrain_file.m2_models:
                    c.execute("""
                        INSERT INTO models
                        (file_id, model_type, filename, format_type)
                        VALUES (?, 'M2', ?, ?)
                    """, (file_id, model, terrain_file.format_type))
                    
                    if known_files:
                        norm = normalize_filename(model)
                        if norm and norm not in known_files:
                            missing_logger.info(f"Missing M2: {model}")
                
                for model in terrain_file.wmo_models:
                    c.execute("""
                        INSERT INTO models
                        (file_id, model_type, filename, format_type)
                        VALUES (?, 'WMO', ?, ?)
                    """, (file_id, model, terrain_file.format_type))
                    
                    if known_files:
                        norm = normalize_filename(model)
                        if norm and norm not in known_files:
                            missing_logger.info(f"Missing WMO: {model}")
                
                # Store MCNK data
                for coord, mcnk in terrain_file.mcnk_chunks.items():
                    c.execute("""
                        INSERT INTO mcnk_data
                        (file_id, tile_x, tile_y, index_x, index_y,
                         flags, area_id, holes, liquid_type)
                        VALUES (?, -1, -1, ?, ?, ?, ?, ?, ?)
                    """, (
                        file_id,
                        mcnk.index_x,
                        mcnk.index_y,
                        int(mcnk.flags),
                        mcnk.area_id,
                        mcnk.holes,
                        mcnk.liquid_type
                    ))
                
            elif isinstance(terrain_file, WDTFile):
                # Store tiles
                for coord, tile in terrain_file.tiles.items():
                    c.execute("""
                        INSERT INTO map_tiles
                        (file_id, coord_x, coord_y, offset, size, flags, async_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        file_id,
                        tile.x,
                        tile.y,
                        tile.offset,
                        tile.size,
                        tile.flags,
                        tile.async_id
                    ))
                
                # Store models
                for model in terrain_file.m2_models:
                    c.execute("""
                        INSERT INTO models
                        (file_id, model_type, filename, format_type)
                        VALUES (?, 'M2', ?, ?)
                    """, (file_id, model.path, model.format_type))
                    
                    if known_files:
                        norm = normalize_filename(model.path)
                        if norm and norm not in known_files:
                            missing_logger.info(f"Missing M2: {model.path}")
                
                for model in terrain_file.wmo_models:
                    c.execute("""
                        INSERT INTO models
                        (file_id, model_type, filename, format_type)
                        VALUES (?, 'WMO', ?, ?)
                    """, (file_id, model.path, model.format_type))
                    
                    if known_files:
                        norm = normalize_filename(model.path)
                        if norm and norm not in known_files:
                            missing_logger.info(f"Missing WMO: {model.path}")
                
                # Create visualization grid
                grid = [[0] * 64 for _ in range(64)]
                for tile in terrain_file.tiles.values():
                    grid[tile.y][tile.x] = 1
                
                # Write visualization
                vis_path = file_path.with_suffix('.vis.txt')
                write_visualization(grid, vis_path)
                logger.info(f"\nGrid visualization saved to: {vis_path}")
            
            conn.commit()
            logger.info("\nProcessing complete")
            logger.info(f"Database: {db_path}")
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error processing file: {e}", exc_info=True)
        sys.exit(1)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='World of Warcraft Terrain Analyzer')
    parser.add_argument('path', help='Path to ADT/WDT file or directory')
    parser.add_argument('--listfile', help='Path to listfile for checking references')
    parser.add_argument('--db', help='Output database path', default='terrain_analysis.db')
    args = parser.parse_args()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger, missing_logger = setup_logging(timestamp)
    
    path = Path(args.path)
    db_path = Path(args.db)
    listfile_path = Path(args.listfile) if args.listfile else None
    
    if path.is_file():
        process_terrain_file(path, listfile_path, db_path, logger, missing_logger)
    elif path.is_dir():
        for file_path in path.glob('*.[aA][dD][tT]'):
            process_terrain_file(file_path, listfile_path, db_path, logger, missing_logger)
        for file_path in path.glob('*.[wW][dD][tT]'):
            process_terrain_file(file_path, listfile_path, db_path, logger, missing_logger)
    else:
        logger.error(f"Path not found: {path}")
        sys.exit(1)

if __name__ == '__main__':
    main()