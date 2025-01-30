"""
Database operations for WDT/ADT parser.
Combines functionality from original analyze_wdt.py database implementation
with improved structure and additional features.
"""
import sqlite3
import struct
import array
from pathlib import Path
import logging
from typing import Dict, Any, List, Tuple, Optional, Union
from datetime import datetime

class DatabaseManager:
    """Manages database operations for WDT/ADT data"""
    
    def __init__(self, db_path: Union[str, Path]):
        """Initialize database manager"""
        self.logger = logging.getLogger('DatabaseManager')
        self.db_path = Path(db_path)
        self.conn = None
        self.setup_database()
    
    def setup_database(self):
        """Setup database schema"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            cursor = self.conn.cursor()
            
            # Create tables
            cursor.executescript('''
                -- WDT records
                CREATE TABLE IF NOT EXISTS wdt_files (
                    id INTEGER PRIMARY KEY,
                    filepath TEXT NOT NULL,
                    map_name TEXT NOT NULL,
                    version INTEGER,
                    flags INTEGER,
                    is_wmo_based BOOLEAN,
                    chunk_order TEXT,
                    format TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(filepath, format)
                );
                
                -- Map tiles
                CREATE TABLE IF NOT EXISTS map_tiles (
                    id INTEGER PRIMARY KEY,
                    wdt_id INTEGER NOT NULL,
                    tile_x INTEGER NOT NULL,
                    tile_y INTEGER NOT NULL,
                    offset INTEGER NOT NULL,
                    size INTEGER NOT NULL,
                    flags INTEGER NOT NULL,
                    async_id INTEGER NOT NULL,
                    FOREIGN KEY (wdt_id) REFERENCES wdt_files(id),
                    UNIQUE(wdt_id, tile_x, tile_y)
                );
                
                -- Textures
                CREATE TABLE IF NOT EXISTS wdt_textures (
                    id INTEGER PRIMARY KEY,
                    wdt_id INTEGER NOT NULL,
                    tile_x INTEGER NOT NULL,
                    tile_y INTEGER NOT NULL,
                    texture_path TEXT NOT NULL,
                    layer_index INTEGER NOT NULL,
                    blend_mode INTEGER NOT NULL DEFAULT 0,
                    has_alpha BOOLEAN NOT NULL DEFAULT 0,
                    is_compressed BOOLEAN NOT NULL DEFAULT 0,
                    effect_id INTEGER NOT NULL DEFAULT 0,
                    flags INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (wdt_id) REFERENCES wdt_files(id)
                );
                
                -- M2 models
                CREATE TABLE IF NOT EXISTS m2_models (
                    id INTEGER PRIMARY KEY,
                    wdt_id INTEGER NOT NULL,
                    tile_x INTEGER NOT NULL,
                    tile_y INTEGER NOT NULL,
                    model_path TEXT NOT NULL,
                    format TEXT NOT NULL,
                    FOREIGN KEY (wdt_id) REFERENCES wdt_files(id)
                );
                
                -- WMO models
                CREATE TABLE IF NOT EXISTS wmo_models (
                    id INTEGER PRIMARY KEY,
                    wdt_id INTEGER NOT NULL,
                    tile_x INTEGER NOT NULL,
                    tile_y INTEGER NOT NULL,
                    model_path TEXT NOT NULL,
                    format TEXT NOT NULL,
                    FOREIGN KEY (wdt_id) REFERENCES wdt_files(id)
                );
                
                -- M2 placements
                CREATE TABLE IF NOT EXISTS m2_placements (
                    id INTEGER PRIMARY KEY,
                    wdt_id INTEGER NOT NULL,
                    tile_x INTEGER NOT NULL,
                    tile_y INTEGER NOT NULL,
                    model_id INTEGER NOT NULL,
                    unique_id INTEGER NOT NULL,
                    position_x REAL NOT NULL,
                    position_y REAL NOT NULL,
                    position_z REAL NOT NULL,
                    rotation_x REAL NOT NULL,
                    rotation_y REAL NOT NULL,
                    rotation_z REAL NOT NULL,
                    scale REAL NOT NULL,
                    flags INTEGER NOT NULL,
                    FOREIGN KEY (wdt_id) REFERENCES wdt_files(id),
                    FOREIGN KEY (model_id) REFERENCES m2_models(id)
                );
                
                -- WMO placements
                CREATE TABLE IF NOT EXISTS wmo_placements (
                    id INTEGER PRIMARY KEY,
                    wdt_id INTEGER NOT NULL,
                    tile_x INTEGER NOT NULL,
                    tile_y INTEGER NOT NULL,
                    model_id INTEGER NOT NULL,
                    unique_id INTEGER NOT NULL,
                    position_x REAL NOT NULL,
                    position_y REAL NOT NULL,
                    position_z REAL NOT NULL,
                    rotation_x REAL NOT NULL,
                    rotation_y REAL NOT NULL,
                    rotation_z REAL NOT NULL,
                    scale REAL NOT NULL,
                    flags INTEGER NOT NULL,
                    doodad_set INTEGER NOT NULL,
                    name_set INTEGER NOT NULL,
                    bounds_min_x REAL NOT NULL,
                    bounds_min_y REAL NOT NULL,
                    bounds_min_z REAL NOT NULL,
                    bounds_max_x REAL NOT NULL,
                    bounds_max_y REAL NOT NULL,
                    bounds_max_z REAL NOT NULL,
                    FOREIGN KEY (wdt_id) REFERENCES wdt_files(id),
                    FOREIGN KEY (model_id) REFERENCES wmo_models(id)
                );
                
                -- MCNK data
                CREATE TABLE IF NOT EXISTS tile_mcnk (
                    id INTEGER PRIMARY KEY,
                    wdt_id INTEGER NOT NULL,
                    tile_x INTEGER NOT NULL,
                    tile_y INTEGER NOT NULL,
                    flags INTEGER NOT NULL,
                    area_id INTEGER NOT NULL,
                    n_layers INTEGER NOT NULL,
                    n_doodad_refs INTEGER NOT NULL,
                    holes INTEGER NOT NULL,
                    liquid_size INTEGER DEFAULT 0,
                    position_x REAL DEFAULT 0,
                    position_y REAL DEFAULT 0,
                    position_z REAL DEFAULT 0,
                    has_vertex_colors BOOLEAN DEFAULT 0,
                    has_shadows BOOLEAN DEFAULT 0,
                    mcvt_offset INTEGER DEFAULT 0,
                    mcnr_offset INTEGER DEFAULT 0,
                    mcly_offset INTEGER DEFAULT 0,
                    mcrf_offset INTEGER DEFAULT 0,
                    mcal_offset INTEGER DEFAULT 0,
                    mcsh_offset INTEGER DEFAULT 0,
                    mclq_offset INTEGER DEFAULT 0,
                    FOREIGN KEY (wdt_id) REFERENCES wdt_files(id)
                );
                
                -- Texture layers
                CREATE TABLE IF NOT EXISTS tile_layers (
                    id INTEGER PRIMARY KEY,
                    wdt_id INTEGER NOT NULL,
                    tile_x INTEGER NOT NULL,
                    tile_y INTEGER NOT NULL,
                    texture_id INTEGER NOT NULL,
                    flags INTEGER NOT NULL,
                    effect_id INTEGER NOT NULL DEFAULT 0,
                    offset_in_mcal INTEGER NOT NULL,
                    FOREIGN KEY (wdt_id) REFERENCES wdt_files(id),
                    FOREIGN KEY (texture_id) REFERENCES wdt_textures(id)
                );
                
                -- Chunk offsets
                CREATE TABLE IF NOT EXISTS chunk_offsets (
                    id INTEGER PRIMARY KEY,
                    wdt_id INTEGER NOT NULL,
                    chunk_name TEXT NOT NULL,
                    offset INTEGER NOT NULL,
                    size INTEGER NOT NULL,
                    data_offset INTEGER NOT NULL,
                    FOREIGN KEY (wdt_id) REFERENCES wdt_files(id)
                );
                
                -- ADT offsets
                CREATE TABLE IF NOT EXISTS adt_offsets (
                    id INTEGER PRIMARY KEY,
                    wdt_id INTEGER NOT NULL,
                    tile_x INTEGER NOT NULL,
                    tile_y INTEGER NOT NULL,
                    mhdr INTEGER NOT NULL DEFAULT 0,
                    mcin INTEGER NOT NULL DEFAULT 0,
                    mtex INTEGER NOT NULL DEFAULT 0,
                    mmdx INTEGER NOT NULL DEFAULT 0,
                    mmid INTEGER NOT NULL DEFAULT 0,
                    mwmo INTEGER NOT NULL DEFAULT 0,
                    mwid INTEGER NOT NULL DEFAULT 0,
                    mddf INTEGER NOT NULL DEFAULT 0,
                    modf INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (wdt_id) REFERENCES wdt_files(id)
                );
                
                -- Height maps with statistics
                CREATE TABLE IF NOT EXISTS height_maps (
                    id INTEGER PRIMARY KEY,
                    wdt_id INTEGER NOT NULL,
                    tile_x INTEGER NOT NULL,
                    tile_y INTEGER NOT NULL,
                    heights BLOB NOT NULL,
                    grid_size INTEGER NOT NULL DEFAULT 145,
                    min_height REAL NOT NULL,
                    max_height REAL NOT NULL,
                    avg_height REAL NOT NULL,
                    FOREIGN KEY (wdt_id) REFERENCES wdt_files(id)
                );
                
                -- Liquid data with enhanced metadata
                CREATE TABLE IF NOT EXISTS liquid_data (
                    id INTEGER PRIMARY KEY,
                    wdt_id INTEGER NOT NULL,
                    tile_x INTEGER NOT NULL,
                    tile_y INTEGER NOT NULL,
                    type INTEGER NOT NULL DEFAULT 0,
                    heights BLOB,
                    flags INTEGER DEFAULT 0,
                    min_height REAL,
                    max_height REAL,
                    FOREIGN KEY (wdt_id) REFERENCES wdt_files(id)
                );
            ''')
            
            self.conn.commit()
            self.logger.info(f"Database initialized: {self.db_path}")
            
        except sqlite3.Error as e:
            self.logger.error(f"Error setting up database: {e}")
            raise

    def batch_insert(self, table: str, columns: List[str], values: List[Tuple]):
        """Helper method for batch inserting records"""
        if not values:
            return []
        
        placeholders = ','.join(['?' for _ in columns])
        query = f'''
            INSERT INTO {table} ({','.join(columns)})
            VALUES ({placeholders})
        '''
        
        cursor = self.conn.cursor()
        cursor.executemany(query, values)
        
        # Get the range of inserted IDs
        first_id = cursor.lastrowid - len(values) + 1
        inserted_ids = list(range(first_id, first_id + len(values)))
        
        self.conn.commit()
        return inserted_ids

    def insert_wdt_record(self, filepath: str, map_name: str, version: Optional[int],
                         flags: Optional[int], is_wmo_based: bool, chunk_order: str,
                         format_type: str) -> int:
        """Insert WDT file record and return its ID"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO wdt_files (
                filepath, map_name, version, flags,
                is_wmo_based, chunk_order, format
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (filepath, map_name, version, flags, is_wmo_based, chunk_order, format_type))
        self.conn.commit()
        return cursor.lastrowid

    def insert_map_tile(self, wdt_id: int, x: int, y: int, offset: int,
                       size: int, flags: int, async_id: int) -> int:
        """Insert map tile record and return its ID"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO map_tiles (
                wdt_id, tile_x, tile_y, offset,
                size, flags, async_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (wdt_id, x, y, offset, size, flags, async_id))
        self.conn.commit()
        return cursor.lastrowid

    def insert_texture(self, wdt_id: int, tile_x: int, tile_y: int,
                      texture_path: str, layer_index: int, blend_mode: int = 0,
                      has_alpha: bool = False, is_compressed: bool = False,
                      effect_id: int = 0, flags: int = 0) -> int:
        """Insert texture record and return its ID"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO wdt_textures (
                wdt_id, tile_x, tile_y, texture_path,
                layer_index, blend_mode, has_alpha,
                is_compressed, effect_id, flags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (wdt_id, tile_x, tile_y, texture_path, layer_index,
              blend_mode, has_alpha, is_compressed, effect_id, flags))
        self.conn.commit()
        return cursor.lastrowid

    def insert_m2_model(self, wdt_id: int, tile_x: int, tile_y: int,
                       model_path: str, format_type: str) -> int:
        """Insert M2 model record and return its ID"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO m2_models (
                wdt_id, tile_x, tile_y,
                model_path, format
            ) VALUES (?, ?, ?, ?, ?)
        ''', (wdt_id, tile_x, tile_y, model_path, format_type))
        self.conn.commit()
        return cursor.lastrowid

    def insert_wmo_model(self, wdt_id: int, tile_x: int, tile_y: int,
                        model_path: str, format_type: str) -> int:
        """Insert WMO model record and return its ID"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO wmo_models (
                wdt_id, tile_x, tile_y,
                model_path, format
            ) VALUES (?, ?, ?, ?, ?)
        ''', (wdt_id, tile_x, tile_y, model_path, format_type))
        self.conn.commit()
        return cursor.lastrowid

    def insert_m2_placement(self, wdt_id: int, tile_x: int, tile_y: int,
                          model_id: int, unique_id: int, position: Tuple[float, float, float],
                          rotation: Tuple[float, float, float], scale: float,
                          flags: int) -> int:
        """Insert M2 placement record and return its ID"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO m2_placements (
                wdt_id, tile_x, tile_y, model_id,
                unique_id, position_x, position_y, position_z,
                rotation_x, rotation_y, rotation_z,
                scale, flags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (wdt_id, tile_x, tile_y, model_id, unique_id,
              position[0], position[1], position[2],
              rotation[0], rotation[1], rotation[2],
              scale, flags))
        self.conn.commit()
        return cursor.lastrowid

    def insert_wmo_placement(self, wdt_id: int, tile_x: int, tile_y: int,
                           model_id: int, unique_id: int, position: Tuple[float, float, float],
                           rotation: Tuple[float, float, float], scale: float,
                           flags: int, doodad_set: int, name_set: int,
                           bounds_min: Tuple[float, float, float],
                           bounds_max: Tuple[float, float, float]) -> int:
        """Insert WMO placement record and return its ID"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO wmo_placements (
                wdt_id, tile_x, tile_y, model_id,
                unique_id, position_x, position_y, position_z,
                rotation_x, rotation_y, rotation_z,
                scale, flags, doodad_set, name_set,
                bounds_min_x, bounds_min_y, bounds_min_z,
                bounds_max_x, bounds_max_y, bounds_max_z
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (wdt_id, tile_x, tile_y, model_id, unique_id,
              position[0], position[1], position[2],
              rotation[0], rotation[1], rotation[2],
              scale, flags, doodad_set, name_set,
              bounds_min[0], bounds_min[1], bounds_min[2],
              bounds_max[0], bounds_max[1], bounds_max[2]))
        self.conn.commit()
        return cursor.lastrowid

    def insert_tile_mcnk(self, wdt_id: int, tile_x: int, tile_y: int,
                        mcnk_data: Dict[str, Any]) -> int:
        """Insert MCNK record with enhanced metadata and return its ID"""
        cursor = self.conn.cursor()
        
        # Extract position and flags
        position = mcnk_data.get('position', {'x': 0.0, 'y': 0.0, 'z': 0.0})
        flags = mcnk_data.get('flags', 0)
        has_vertex_colors = bool(mcnk_data.get('has_vertex_colors', False))
        has_shadows = bool(mcnk_data.get('has_shadows', False))
        
        cursor.execute('''
            INSERT INTO tile_mcnk (
                wdt_id, tile_x, tile_y, flags,
                area_id, n_layers, n_doodad_refs,
                holes, liquid_size,
                position_x, position_y, position_z,
                has_vertex_colors, has_shadows,
                mcvt_offset, mcnr_offset, mcly_offset,
                mcrf_offset, mcal_offset, mcsh_offset,
                mclq_offset
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            wdt_id, tile_x, tile_y, flags,
            mcnk_data.get('area_id', 0),
            mcnk_data.get('n_layers', 0),
            mcnk_data.get('n_doodad_refs', 0),
            mcnk_data.get('holes', 0),
            mcnk_data.get('liquid_size', 0),
            position.get('x', 0.0),
            position.get('y', 0.0),
            position.get('z', 0.0),
            has_vertex_colors,
            has_shadows,
            mcnk_data.get('mcvt_offset', 0),
            mcnk_data.get('mcnr_offset', 0),
            mcnk_data.get('mcly_offset', 0),
            mcnk_data.get('mcrf_offset', 0),
            mcnk_data.get('mcal_offset', 0),
            mcnk_data.get('mcsh_offset', 0),
            mcnk_data.get('mclq_offset', 0)
        ))
        self.conn.commit()
        return cursor.lastrowid

    def insert_tile_layer(self, wdt_id: int, tile_x: int, tile_y: int,
                         texture_id: int, flags: int, effect_id: int,
                         offset_in_mcal: int) -> int:
        """Insert texture layer record and return its ID"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO tile_layers (
                wdt_id, tile_x, tile_y,
                texture_id, flags, effect_id,
                offset_in_mcal
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (wdt_id, tile_x, tile_y, texture_id,
              flags, effect_id, offset_in_mcal))
        self.conn.commit()
        return cursor.lastrowid

    def insert_chunk_offset(self, wdt_id: int, chunk_name: str,
                          offset: int, size: int, data_offset: int) -> int:
        """Insert chunk offset record and return its ID"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO chunk_offsets (
                wdt_id, chunk_name, offset,
                size, data_offset
            ) VALUES (?, ?, ?, ?, ?)
        ''', (wdt_id, chunk_name, offset, size, data_offset))
        self.conn.commit()
        return cursor.lastrowid

    def insert_adt_offsets(self, wdt_id: int, tile_x: int, tile_y: int,
                          offsets: Dict[str, int]) -> int:
        """Insert ADT offsets record and return its ID"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO adt_offsets (
                wdt_id, tile_x, tile_y,
                mhdr, mcin, mtex, mmdx, mmid,
                mwmo, mwid, mddf, modf
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (wdt_id, tile_x, tile_y,
              offsets.get('MHDR', 0), offsets.get('MCIN', 0),
              offsets.get('MTEX', 0), offsets.get('MMDX', 0),
              offsets.get('MMID', 0), offsets.get('MWMO', 0),
              offsets.get('MWID', 0), offsets.get('MDDF', 0),
              offsets.get('MODF', 0)))
        self.conn.commit()
        return cursor.lastrowid

    def insert_height_map(self, wdt_id: int, tile_x: int, tile_y: int,
                         heights: Union[List[float], array.array]) -> int:
        """Insert height map record with statistics and return its ID"""
        cursor = self.conn.cursor()
        
        # Convert to list if array
        if isinstance(heights, array.array):
            heights = list(heights)
        
        # Calculate statistics
        min_height = min(heights)
        max_height = max(heights)
        avg_height = sum(heights) / len(heights)
        
        # Convert to binary blob
        heights_blob = b''.join(struct.pack('<f', h) for h in heights)
        
        cursor.execute('''
            INSERT INTO height_maps (
                wdt_id, tile_x, tile_y,
                heights, grid_size,
                min_height, max_height, avg_height
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (wdt_id, tile_x, tile_y,
              heights_blob, len(heights),
              min_height, max_height, avg_height))
        self.conn.commit()
        return cursor.lastrowid

    def insert_liquid_data(self, wdt_id: int, tile_x: int, tile_y: int,
                          type_id: int, heights: Optional[Union[List[float], array.array]] = None,
                          flags: Optional[int] = None) -> int:
        """Insert liquid data record with enhanced metadata and return its ID"""
        cursor = self.conn.cursor()
        
        # Process heights if present
        if heights is not None:
            if isinstance(heights, array.array):
                heights = list(heights)
            min_height = min(heights)
            max_height = max(heights)
            heights_blob = b''.join(struct.pack('<f', h) for h in heights)
        else:
            min_height = max_height = None
            heights_blob = None
        
        cursor.execute('''
            INSERT INTO liquid_data (
                wdt_id, tile_x, tile_y,
                type, heights, flags,
                min_height, max_height
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (wdt_id, tile_x, tile_y, type_id,
              heights_blob, flags,
              min_height, max_height))
        self.conn.commit()
        return cursor.lastrowid

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None