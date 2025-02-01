"""
Multi-threaded database builder for terrain data.
Takes JSON files and constructs SQLite database efficiently.
"""
import os
import json
import sqlite3
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from queue import Queue

from terrain_structures import TerrainFile, ADTFile, WDTFile, ChunkInfo
from terrain_database import (
    setup_database, compress_array,
    insert_mcnk_data, insert_height_map, insert_liquid_data,
    insert_chunk_offset, insert_m2_placement, insert_wmo_placement,
    insert_map_tile, insert_texture, insert_texture_layer,
    insert_normal_data
)
from json_handler import load_from_json

class DatabaseBuilder:
    """Multi-threaded database builder"""
    
    def __init__(self, db_path: Path, json_dir: Path, max_workers: int = None):
        """
        Initialize database builder
        
        Args:
            db_path: Path to output database
            json_dir: Directory containing JSON files
            max_workers: Maximum number of worker threads
        """
        self.db_path = db_path
        self.json_dir = json_dir
        self.max_workers = max_workers or os.cpu_count()
        self.logger = logging.getLogger('db_builder')
        
        # Thread-local storage for database connections
        self.local = threading.local()
        
        # Queues for coordinating work
        self.file_queue = Queue()
        self.model_queue = Queue()
        self.texture_queue = Queue()
        
    def get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self.local, 'connection'):
            self.local.connection = sqlite3.connect(self.db_path)
        return self.local.connection
        
    def close_connections(self):
        """Close all thread-local connections"""
        if hasattr(self.local, 'connection'):
            self.local.connection.close()
            delattr(self.local, 'connection')
            
    def process_file(self, json_path: Path) -> Tuple[int, List[Dict]]:
        """
        Process a single JSON file
        
        Args:
            json_path: Path to JSON file
            
        Returns:
            Tuple of (file_id, texture_data)
        """
        try:
            # Load terrain data
            terrain_file = load_from_json(json_path)
            
            # Get database connection
            conn = self.get_connection()
            c = conn.cursor()
            
            # Insert file record
            c.execute("""
                INSERT INTO terrain_files
                (filename, file_type, format_type, map_name, version, flags, chunk_order)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                terrain_file.path,
                terrain_file.file_type,
                terrain_file.format_type,
                terrain_file.map_name,
                terrain_file.version,
                int(terrain_file.flags),
                ','.join(terrain_file.chunk_order)
            ))
            file_id = c.lastrowid
            
            # Collect texture data
            texture_data = []
            
            if isinstance(terrain_file, ADTFile):
                
                # Collect textures
                for tex in terrain_file.textures:
                    texture_data.append({
                        'file_id': file_id,
                        'tile_x': -1,
                        'tile_y': -1,
                        'filename': tex.filename,
                        'flags': tex.flags,
                        'effect_id': tex.effect_id
                    })
                
                # Store MCNK data and related chunks
                for coord, mcnk in terrain_file.mcnk_chunks.items():
                    # Get coordinates from the tuple
                    x, y = coord
                    
                    # Store MCNK info
                    insert_mcnk_data(conn, file_id, mcnk, x, y)
                    
                    # Store height map if available
                    if hasattr(mcnk, 'height_map') and mcnk.height_map:
                        insert_height_map(conn, file_id, x, y, mcnk.height_map)
                    
                    # Store normal data if available
                    if hasattr(mcnk, 'normal_data') and mcnk.normal_data:
                        insert_normal_data(conn, file_id, x, y, mcnk.normal_data)
                    
                    # Store liquid data if available
                    if hasattr(mcnk, 'liquid_heights') and mcnk.liquid_heights:
                        insert_liquid_data(conn, file_id, x, y,
                                        mcnk.liquid_heights,
                                        mcnk.liquid_flags if hasattr(mcnk, 'liquid_flags') else None)
                    
                    # Store chunk offsets from subchunks
                    if coord in terrain_file.subchunks:
                        for chunk_name, chunk_info in terrain_file.subchunks[coord].items():
                            # chunk_info is a dictionary with offset, size, data_offset
                            insert_chunk_offset(conn, file_id, chunk_name,
                                            chunk_info['offset'], chunk_info['size'],
                                            chunk_info['data_offset'])
                    
                    # Store texture layers and alpha maps
                    if hasattr(mcnk, 'texture_layers') and mcnk.texture_layers:
                        for layer in mcnk.texture_layers:
                            insert_texture_layer(conn, file_id, x, y, layer)
                
                # Store M2 placements
                for placement in terrain_file.m2_placements:
                    model_name = terrain_file.m2_models[placement.name_id]
                    insert_m2_placement(conn, file_id, placement, model_name, -1, -1)
                
                # Store WMO placements
                for placement in terrain_file.wmo_placements:
                    model_name = terrain_file.wmo_models[placement.name_id]
                    insert_wmo_placement(conn, file_id, placement, model_name, -1, -1)
                    
            elif isinstance(terrain_file, WDTFile):
                # Store tiles
                for coord, tile in terrain_file.tiles.items():
                    insert_map_tile(conn, file_id, tile)
                
                # Store M2 placements
                for placement in terrain_file.m2_placements:
                    model_ref = terrain_file.m2_models[placement.name_id]
                    insert_m2_placement(conn, file_id, placement, model_ref.path, -1, -1)
                
                # Store WMO placements
                for placement in terrain_file.wmo_placements:
                    model_ref = terrain_file.wmo_models[placement.name_id]
                    insert_wmo_placement(conn, file_id, placement, model_ref.path, -1, -1)
                
                # Store chunk offsets
                for chunk_name, chunk_info in terrain_file.chunk_offsets.items():
                    insert_chunk_offset(conn, file_id, chunk_name,
                                     chunk_info.offset, chunk_info.size,
                                     chunk_info.data_offset)
            
            conn.commit()
            return file_id, texture_data
            
        except Exception as e:
            self.logger.error(f"Error processing {json_path}: {e}", exc_info=True)
            if hasattr(self.local, 'connection'):
                self.local.connection.rollback()
            return None, []
            
    def batch_insert_textures(self, textures: List[Dict]):
        """Batch insert textures"""
        if not textures:
            return
            
        conn = self.get_connection()
        c = conn.cursor()
        
        try:
            c.executemany("""
                INSERT INTO textures
                (file_id, tile_x, tile_y, filename, flags, effect_id)
                VALUES (:file_id, :tile_x, :tile_y, :filename, :flags, :effect_id)
            """, textures)
            conn.commit()
        except Exception as e:
            self.logger.error(f"Error inserting textures: {e}", exc_info=True)
            conn.rollback()
            
    def build_database(self):
        """Build database from JSON files"""
        # Initialize database schema
        setup_database(str(self.db_path))
        
        # Find all JSON files
        json_files = list(self.json_dir.glob('*.json'))
        total_files = len(json_files)
        self.logger.info(f"Found {total_files} JSON files to process")
        
        # Process files in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit file processing jobs
            future_to_path = {
                executor.submit(self.process_file, path): path
                for path in json_files
            }
            
            # Collect texture data
            all_textures = []
            
            # Process results as they complete
            completed = 0
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    file_id, textures = future.result()
                    if file_id is not None:
                        all_textures.extend(textures)
                    completed += 1
                    if completed % 100 == 0:
                        self.logger.info(f"Processed {completed}/{total_files} files")
                except Exception as e:
                    self.logger.error(f"Error processing {path}: {e}", exc_info=True)
            
            # Batch insert textures
            if all_textures:
                self.logger.info("Inserting textures...")
                self.batch_insert_textures(all_textures)
            
        self.logger.info("Database construction complete")
        self.close_connections()

def build_database(json_dir: Path, db_path: Path, max_workers: Optional[int] = None):
    """
    Build database from JSON files
    
    Args:
        json_dir: Directory containing JSON files
        db_path: Path to output database
        max_workers: Maximum number of worker threads
    """
    builder = DatabaseBuilder(db_path, json_dir, max_workers)
    builder.build_database()