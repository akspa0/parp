"""
Database operations for WoW terrain data.
Provides high-level interface for database interactions.
"""
import sqlite3
import zlib
import array
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from concurrent.futures import ThreadPoolExecutor

from ..models import (
    TerrainFile, ADTFile, WDTFile,
    TextureInfo, ModelReference, ModelPlacement, WMOPlacement,
    MCNKInfo, MapTile, TextureLayer
)
from ..utils import get_logger

def compress_array(data: List[float]) -> bytes:
    """Compress float array to binary"""
    arr = array.array('f', data)
    return zlib.compress(arr.tobytes())

class DatabaseManager:
    """Manages database operations for terrain data"""
    
    def __init__(self, db_path: Path):
        """
        Initialize database manager
        
        Args:
            db_path: Path to database file
        """
        self.db_path = Path(db_path)
        self.logger = get_logger('db_manager')
        
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        return sqlite3.connect(self.db_path)
        
    def insert_terrain_file(self, conn: sqlite3.Connection, file: TerrainFile) -> int:
        """Insert terrain file record"""
        c = conn.cursor()
        c.execute("""
            INSERT INTO terrain_files
            (filename, file_type, format_type, map_name, version, flags, chunk_order)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(file.path),
            file.file_type,
            file.format_type,
            file.map_name,
            file.version,
            file.flags.value,  # Get raw integer value from Flag enum
            ','.join(file.chunk_order)
        ))
        return c.lastrowid
        
    def insert_map_tile(self, conn: sqlite3.Connection, file_id: int,
                       tile: MapTile, x: int, y: int) -> int:
        """Insert map tile record"""
        c = conn.cursor()
        c.execute("""
            INSERT INTO map_tiles
            (file_id, coord_x, coord_y, offset, size, flags, async_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            file_id, x, y,
            tile.offset, tile.size,
            tile.flags, tile.async_id
        ))
        return c.lastrowid
        
    def insert_texture(self, conn: sqlite3.Connection, file_id: int,
                      texture: TextureInfo, x: int, y: int) -> int:
        """Insert texture record"""
        c = conn.cursor()
        c.execute("""
            INSERT INTO textures
            (file_id, tile_x, tile_y, filename, layer_index,
             blend_mode, has_alpha, is_compressed, effect_id, flags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            file_id, x, y,
            texture.filename,
            texture.layer_index,
            texture.blend_mode,
            0,  # has_alpha
            1 if texture.is_compressed else 0,
            texture.effect_id,
            texture.flags
        ))
        return c.lastrowid
        
    def insert_texture_layer(self, conn: sqlite3.Connection, file_id: int,
                           layer: TextureLayer, x: int, y: int) -> int:
        """Insert texture layer and alpha map"""
        c = conn.cursor()
        
        # Insert layer
        c.execute("""
            INSERT INTO texture_layers
            (file_id, mcnk_index_x, mcnk_index_y, texture_id,
             flags, effect_id, layer_index, blend_mode, is_compressed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            file_id, x, y,
            layer.texture_id,
            layer.flags,
            layer.effect_id,
            layer.layer_index,
            layer.blend_mode,
            1 if layer.is_compressed else 0
        ))
        layer_id = c.lastrowid
        
        # Insert alpha map if available
        if layer.alpha_map:
            c.execute("""
                INSERT INTO alpha_maps
                (layer_id, alpha_data)
                VALUES (?, ?)
            """, (
                layer_id,
                compress_array(layer.alpha_map)
            ))
            
        return layer_id
        
    def insert_model(self, conn: sqlite3.Connection, file_id: int,
                    model: Union[str, ModelReference], model_type: str) -> int:
        """Insert model record"""
        c = conn.cursor()
        
        if isinstance(model, str):
            filename = model
            format_type = 'retail'
        else:
            filename = model.path
            format_type = model.format_type
            
        c.execute("""
            INSERT INTO models
            (file_id, model_type, filename, format_type)
            VALUES (?, ?, ?, ?)
        """, (
            file_id,
            model_type,
            filename,
            format_type
        ))
        return c.lastrowid
        
    def insert_model_placement(self, conn: sqlite3.Connection, file_id: int,
                             placement: Union[ModelPlacement, WMOPlacement],
                             filename: str, x: int, y: int) -> int:
        """Insert model placement record"""
        c = conn.cursor()
        
        if isinstance(placement, WMOPlacement):
            c.execute("""
                INSERT INTO wmo_placements
                (file_id, tile_x, tile_y, unique_id, filename,
                 pos_x, pos_y, pos_z, rot_x, rot_y, rot_z,
                 scale, flags, doodad_set, name_set,
                 bounds_min_x, bounds_min_y, bounds_min_z,
                 bounds_max_x, bounds_max_y, bounds_max_z)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_id, x, y,
                placement.unique_id, filename,
                placement.position.x, placement.position.y, placement.position.z,
                placement.rotation.x, placement.rotation.y, placement.rotation.z,
                placement.scale, placement.flags,
                placement.doodad_set, placement.name_set,
                placement.bounding_box.min.x, placement.bounding_box.min.y, placement.bounding_box.min.z,
                placement.bounding_box.max.x, placement.bounding_box.max.y, placement.bounding_box.max.z
            ))
        else:
            c.execute("""
                INSERT INTO m2_placements
                (file_id, tile_x, tile_y, unique_id, filename,
                 pos_x, pos_y, pos_z, rot_x, rot_y, rot_z,
                 scale, flags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_id, x, y,
                placement.unique_id, filename,
                placement.position.x, placement.position.y, placement.position.z,
                placement.rotation.x, placement.rotation.y, placement.rotation.z,
                placement.scale, placement.flags
            ))
            
        return c.lastrowid
        
    def insert_mcnk_data(self, conn: sqlite3.Connection, file_id: int,
                        mcnk: MCNKInfo, x: int, y: int) -> None:
        """Insert all MCNK-related data"""
        c = conn.cursor()
        
        try:
            # Insert MCNK info
            c.execute("""
                INSERT INTO mcnk_data
                (file_id, tile_x, tile_y, index_x, index_y,
                 flags, area_id, holes, liquid_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_id, x, y,
                mcnk.index_x, mcnk.index_y,
                mcnk.flags.value, mcnk.area_id,  # Get raw integer value from Flag enum
                mcnk.holes, mcnk.liquid_type
            ))
            
            # Insert height map
            if mcnk.height_map:
                c.execute("""
                    INSERT INTO height_maps
                    (file_id, tile_x, tile_y, heights)
                    VALUES (?, ?, ?, ?)
                """, (
                    file_id, x, y,
                    compress_array(mcnk.height_map)
                ))
                
            # Insert normal data
            if mcnk.normal_data:
                c.execute("""
                    INSERT INTO normal_data
                    (file_id, tile_x, tile_y, normals)
                    VALUES (?, ?, ?, ?)
                """, (
                    file_id, x, y,
                    compress_array(mcnk.normal_data)
                ))
                
            # Insert liquid data
            if mcnk.liquid_heights:
                c.execute("""
                    INSERT INTO liquid_data
                    (file_id, tile_x, tile_y, heights, flags)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    file_id, x, y,
                    compress_array(mcnk.liquid_heights),
                    compress_array(mcnk.liquid_flags) if mcnk.liquid_flags else None
                ))
                
        except Exception as e:
            self.logger.error(f"Error inserting MCNK data at {x},{y}: {e}", exc_info=True)
            raise
            
    def process_terrain_file(self, file: TerrainFile) -> None:
        """Process a terrain file and insert all its data"""
        conn = self.get_connection()
        try:
            # Begin transaction
            conn.execute("BEGIN")
            
            # Insert file record
            file_id = self.insert_terrain_file(conn, file)
            
            if isinstance(file, ADTFile):
                # Process ADT file
                self._process_adt(conn, file_id, file)
            else:
                # Process WDT file
                self._process_wdt(conn, file_id, file)
                
            # Commit transaction
            conn.commit()
            
        except Exception as e:
            self.logger.error(f"Error processing {file.path}: {e}", exc_info=True)
            conn.rollback()
            raise
            
        finally:
            conn.close()
            
    def _process_adt(self, conn: sqlite3.Connection, file_id: int, file: ADTFile) -> None:
        """Process ADT file data"""
        # Insert textures
        for tex in file.textures:
            self.insert_texture(conn, file_id, tex, -1, -1)
            
        # Insert models
        for model in file.m2_models:
            self.insert_model(conn, file_id, model, 'M2')
        for model in file.wmo_models:
            self.insert_model(conn, file_id, model, 'WMO')
            
        # Process MCNK chunks
        for (x, y), mcnk in file.mcnk_chunks.items():
            self.insert_mcnk_data(conn, file_id, mcnk, x, y)
            
            # Process texture layers
            if mcnk.texture_layers:
                for layer in mcnk.texture_layers:
                    self.insert_texture_layer(conn, file_id, layer, x, y)
                    
        # Insert model placements
        for placement in file.m2_placements:
            model_name = file.m2_models[placement.name_id]
            x = int(placement.position.x / 533.33333)
            y = int(placement.position.y / 533.33333)
            self.insert_model_placement(conn, file_id, placement, model_name, x, y)
            
        for placement in file.wmo_placements:
            model_name = file.wmo_models[placement.name_id]
            x = int(placement.position.x / 533.33333)
            y = int(placement.position.y / 533.33333)
            self.insert_model_placement(conn, file_id, placement, model_name, x, y)
            
    def _process_wdt(self, conn: sqlite3.Connection, file_id: int, file: WDTFile) -> None:
        """Process WDT file data"""
        # Insert map tiles
        for (x, y), tile in file.tiles.items():
            self.insert_map_tile(conn, file_id, tile, x, y)
            
        # Insert models
        for model in file.m2_models:
            self.insert_model(conn, file_id, model, 'M2')
        for model in file.wmo_models:
            self.insert_model(conn, file_id, model, 'WMO')
            
        # Insert model placements
        for placement in file.m2_placements:
            model_ref = file.m2_models[placement.name_id]
            x = int(placement.position.x / 533.33333)
            y = int(placement.position.y / 533.33333)
            self.insert_model_placement(conn, file_id, placement, model_ref.path, x, y)
            
        for placement in file.wmo_placements:
            model_ref = file.wmo_models[placement.name_id]
            x = int(placement.position.x / 533.33333)
            y = int(placement.position.y / 533.33333)
            self.insert_model_placement(conn, file_id, placement, model_ref.path, x, y)
            
    def build_from_json(self, json_dir: Path, max_workers: Optional[int] = None,
                       limit: Optional[int] = None) -> None:
        """
        Build database from JSON files
        
        Args:
            json_dir: Directory containing JSON files
            max_workers: Maximum number of worker threads
            limit: Maximum number of files to process
        """
        from ..json import JSONHandler
        from .schema import init_database
        
        # Initialize database
        init_database(self.db_path)
        
        # Find JSON files
        json_files = list(json_dir.glob('*.json'))
        if limit:
            json_files = json_files[:limit]
            
        total_files = len(json_files)
        self.logger.info(f"Found {total_files} JSON files to process")
        
        if total_files == 0:
            return
            
        # Process files in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all files for processing
            future_to_path = {
                executor.submit(self._process_json_file, path): path
                for path in json_files
            }
            
            # Process results as they complete
            completed = 0
            for future in executor.as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    future.result()
                    completed += 1
                    if completed % 100 == 0 or completed == total_files:
                        self.logger.info(f"Processed {completed}/{total_files} files")
                except Exception as e:
                    self.logger.error(f"Error processing {path}: {e}", exc_info=True)
                    
        self.logger.info("Database construction complete")
        
    def _process_json_file(self, json_path: Path) -> None:
        """Process a single JSON file"""
        from ..json import JSONHandler
        
        try:
            # Load terrain file from JSON
            terrain_file = JSONHandler.load(json_path)
            
            # Process terrain file
            self.process_terrain_file(terrain_file)
            
        except Exception as e:
            self.logger.error(f"Error processing {json_path}: {e}", exc_info=True)
            raise