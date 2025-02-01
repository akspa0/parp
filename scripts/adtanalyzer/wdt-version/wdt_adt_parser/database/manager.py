"""
Database manager for WDT/ADT parsing.
Implements the same functionality as wdt_db.py.
"""
import sqlite3
import logging
from pathlib import Path
from typing import Optional, Tuple, List, Any, Dict, Union
from array import array

from .schema import DatabaseSchema

class DatabaseManager:
    """Manages database operations for WDT/ADT parsing"""
    
    def __init__(self, db_path: Union[str, Path]):
        """
        Initialize database manager
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.conn = DatabaseSchema.setup_database(self.db_path)
        self.logger = logging.getLogger('DatabaseManager')
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def insert_wdt_record(self, filename: str, map_name: str, version: Optional[int],
                         flags: Optional[int], is_wmo_based: bool = False,
                         chunk_order: Optional[str] = None,
                         original_format: Optional[str] = None) -> int:
        """Insert WDT file record"""
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO wdt_files (
            filename, map_name, version, flags,
            is_wmo_based, chunk_order, original_format
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (filename, map_name, version, flags,
              is_wmo_based, chunk_order, original_format))
        self.conn.commit()
        return cursor.lastrowid
    
    def insert_chunk_offset(self, wdt_id: int, chunk_name: str,
                          offset: int, size: int, data_offset: int) -> int:
        """Insert chunk offset information"""
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO chunk_offsets (
            wdt_id, chunk_name, offset, size, data_offset
        )
        VALUES (?, ?, ?, ?, ?)
        ''', (wdt_id, chunk_name, offset, size, data_offset))
        self.conn.commit()
        return cursor.lastrowid
    
    def insert_adt_offsets(self, wdt_id: int, tile_x: int, tile_y: int,
                          offsets: Dict[str, int]) -> int:
        """Insert ADT chunk offset information"""
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO adt_offsets (
            wdt_id, tile_x, tile_y,
            mhdr_offset, mcin_offset, mtex_offset,
            mmdx_offset, mmid_offset, mwmo_offset,
            mwid_offset, mddf_offset, modf_offset
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            wdt_id, tile_x, tile_y,
            offsets.get('MHDR', 0), offsets.get('MCIN', 0),
            offsets.get('MTEX', 0), offsets.get('MMDX', 0),
            offsets.get('MMID', 0), offsets.get('MWMO', 0),
            offsets.get('MWID', 0), offsets.get('MDDF', 0),
            offsets.get('MODF', 0)
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def insert_map_tile(self, wdt_id: int, x: int, y: int,
                       offset: int, size: int, flags: int,
                       async_id: int) -> int:
        """Insert map tile record"""
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO map_tiles (
            wdt_id, tile_x, tile_y, offset,
            size, flags, async_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (wdt_id, x, y, offset, size, flags, async_id))
        self.conn.commit()
        return cursor.lastrowid
    
    def insert_tile_mcnk(self, wdt_id: int, tile_x: int, tile_y: int,
                        mcnk_data: Dict[str, Any]) -> int:
        """Insert MCNK data for a specific tile"""
        cursor = self.conn.cursor()
        
        position = mcnk_data.get('position', {'x': 0.0, 'y': 0.0, 'z': 0.0})
        liquid = mcnk_data.get('liquid', {'size': 0})
        
        flags = mcnk_data['flags']
        has_vertex_colors = 1 if isinstance(flags, dict) and flags.get('has_vertex_colors') else 0
        has_shadows = 1 if isinstance(flags, dict) and flags.get('has_mcsh') else 0
        
        cursor.execute('''
        INSERT INTO tile_mcnk (
            wdt_id, tile_x, tile_y, flags, layers, doodad_refs,
            mcvt_offset, mcnr_offset, mcly_offset, mcrf_offset,
            mcal_offset, mcsh_offset, mclq_offset,
            area_id, holes, liquid_size,
            position_x, position_y, position_z,
            has_vertex_colors, has_shadows
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            wdt_id, tile_x, tile_y,
            mcnk_data['flags'], mcnk_data['n_layers'], mcnk_data['n_doodad_refs'],
            mcnk_data['mcvt_offset'], mcnk_data['mcnr_offset'], mcnk_data['mcly_offset'],
            mcnk_data['mcrf_offset'], mcnk_data['mcal_offset'], mcnk_data['mcsh_offset'],
            mcnk_data['mclq_offset'],
            mcnk_data.get('area_id', 0), mcnk_data.get('holes', 0), liquid['size'],
            position['x'], position['y'], position['z'],
            has_vertex_colors, has_shadows
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def insert_tile_layer(self, tile_mcnk_id: int, layer_index: int,
                         texture_id: int, flags: int, effect_id: int) -> int:
        """Insert layer data for a tile"""
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO tile_layers (
            tile_mcnk_id, layer_index, texture_id,
            flags, effect_id
        )
        VALUES (?, ?, ?, ?, ?)
        ''', (tile_mcnk_id, layer_index, texture_id, flags, effect_id))
        self.conn.commit()
        return cursor.lastrowid
    
    def insert_texture(self, wdt_id: int, tile_x: int, tile_y: int,
                      texture_path: str, layer_index: int,
                      blend_mode: int = 0, has_alpha: int = 0,
                      is_compressed: int = 0, effect_id: int = 0,
                      flags: int = 0) -> int:
        """Insert texture record"""
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO wdt_textures (
            wdt_id, tile_x, tile_y, texture_path, layer_index,
            blend_mode, has_alpha, is_compressed, effect_id, flags
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            wdt_id, tile_x, tile_y, texture_path, layer_index,
            blend_mode, has_alpha, is_compressed, effect_id, flags
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def insert_m2_model(self, wdt_id: int, tile_x: int, tile_y: int,
                       model_path: str, format_type: str) -> int:
        """Insert M2 model record"""
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO m2_models (
            wdt_id, tile_x, tile_y, model_path, format_type
        )
        VALUES (?, ?, ?, ?, ?)
        ''', (wdt_id, tile_x, tile_y, model_path, format_type))
        self.conn.commit()
        return cursor.lastrowid
    
    def insert_wmo_model(self, wdt_id: int, tile_x: int, tile_y: int,
                        model_path: str, format_type: str) -> int:
        """Insert WMO model record"""
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO wmo_models (
            wdt_id, tile_x, tile_y, model_path, format_type
        )
        VALUES (?, ?, ?, ?, ?)
        ''', (wdt_id, tile_x, tile_y, model_path, format_type))
        self.conn.commit()
        return cursor.lastrowid
    
    def insert_m2_placement(self, wdt_id: int, tile_x: int, tile_y: int,
                          model_id: int, unique_id: int,
                          position: Tuple[float, float, float],
                          rotation: Tuple[float, float, float],
                          scale: float, flags: int) -> int:
        """Insert M2 placement record"""
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO m2_placements (
            wdt_id, tile_x, tile_y, model_id, unique_id,
            position_x, position_y, position_z,
            rotation_x, rotation_y, rotation_z,
            scale, flags
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            wdt_id, tile_x, tile_y, model_id, unique_id,
            position[0], position[1], position[2],
            rotation[0], rotation[1], rotation[2],
            scale, flags
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def insert_height_map(self, tile_mcnk_id: int,
                         height_data: array) -> int:
        """Insert height map data for a tile"""
        cursor = self.conn.cursor()
        
        heights = list(height_data)
        min_height = min(heights)
        max_height = max(heights)
        avg_height = sum(heights) / len(heights)
        
        cursor.execute('''
        INSERT INTO height_map_info (
            tile_mcnk_id, height_data, grid_size,
            min_height, max_height, avg_height
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            tile_mcnk_id,
            height_data.tobytes(),
            len(heights),
            min_height,
            max_height,
            avg_height
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def insert_liquid_data(self, tile_mcnk_id: int,
                          liquid_type: int,
                          liquid_heights: Optional[array]) -> int:
        """Insert liquid data for a tile"""
        cursor = self.conn.cursor()
        
        if liquid_heights:
            heights = list(liquid_heights)
            min_height = min(heights)
            max_height = max(heights)
        else:
            min_height = max_height = 0.0
        
        cursor.execute('''
        INSERT INTO liquid_data (
            tile_mcnk_id, liquid_type, liquid_data,
            min_height, max_height
        )
        VALUES (?, ?, ?, ?, ?)
        ''', (
            tile_mcnk_id,
            liquid_type,
            liquid_heights.tobytes() if liquid_heights else None,
            min_height,
            max_height
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def insert_wmo_placement(self, wdt_id: int, tile_x: int, tile_y: int,
                           model_id: int, unique_id: int,
                           position: Tuple[float, float, float],
                           rotation: Tuple[float, float, float],
                           scale: float, flags: int,
                           doodad_set: int, name_set: int,
                           bounds_min: Tuple[float, float, float],
                           bounds_max: Tuple[float, float, float]) -> int:
        """Insert WMO placement record"""
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO wmo_placements (
            wdt_id, tile_x, tile_y, model_id, unique_id,
            position_x, position_y, position_z,
            rotation_x, rotation_y, rotation_z,
            scale, flags, doodad_set, name_set,
            bounds_min_x, bounds_min_y, bounds_min_z,
            bounds_max_x, bounds_max_y, bounds_max_z
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            wdt_id, tile_x, tile_y, model_id, unique_id,
            position[0], position[1], position[2],
            rotation[0], rotation[1], rotation[2],
            scale, flags, doodad_set, name_set,
            bounds_min[0], bounds_min[1], bounds_min[2],
            bounds_max[0], bounds_max[1], bounds_max[2]
        ))
        self.conn.commit()
        return cursor.lastrowid