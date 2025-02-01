"""
Database management for WDT/ADT parsing.
"""
import sqlite3
from typing import List, Optional, Dict, Any, Union, Tuple
from pathlib import Path
import json
import logging
from datetime import datetime
from .adt_parser.mcnk_decoders import MCNKHeader, MCNKFlags
from .adt_parser.adt_parser import ADTFile

class DatabaseError(Exception):
    """Custom database error class"""
    pass

class DatabaseManager:
    """Manages SQLite database operations"""
    
    def __init__(self, db_path: Union[str, Path]):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.logger = logging.getLogger('DatabaseManager')
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        
        # Initialize database versioning
        self._init_versioning()
        
        # Create tables if they don't exist
        self._create_tables()
        
        # Add indexes and constraints
        self._add_indexes()
        self._add_constraints()
        
    def _add_indexes(self):
        """Add database indexes for common queries"""
        with self.conn:
            # Indexes for tile_mcnk table
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tile_mcnk_wdt_id
                ON tile_mcnk(wdt_id)
            """)
            
            # Indexes for height_maps table
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_height_maps_wdt_id
                ON height_maps(wdt_id)
            """)
            
            # Indexes for liquid_data table
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_liquid_data_tile_mcnk_id
                ON liquid_data(tile_mcnk_id)
            """)
            
    def _add_constraints(self):
        """Add database constraints for data integrity"""
        with self.conn:
            # Enable foreign key support
            self.conn.execute("PRAGMA foreign_keys = ON")
            
            # Add unique constraint on wdt_files.path
            self.conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_wdt_path
                ON wdt_files(path)
            """)
            
    def _init_versioning(self):
        """Initialize database version tracking"""
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS db_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Get current version
            version = self.conn.execute("""
                SELECT MAX(version) as version FROM db_version
            """).fetchone()['version'] or 0
            
            # Apply migrations if needed
            if version < 1:
                self._apply_migration_1()
                self.conn.execute("""
                    INSERT INTO db_version (version) VALUES (1)
                """)
                
    def _apply_migration_1(self):
        """Apply initial schema migration"""
        # No-op since we're creating fresh tables
        pass
        
        self.logger.info(f"Database initialized: {self.db_path}")
    
    def _create_tables(self):
        """Create database tables if they don't exist"""
        with self.conn:
            # WDT records
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS wdt_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT NOT NULL,
                    map_name TEXT NOT NULL,
                    version INTEGER,
                    flags INTEGER,
                    wmo_only BOOLEAN,
                    chunk_order TEXT,
                    format TEXT NOT NULL,
                    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Map tiles
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS map_tiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wdt_id INTEGER NOT NULL,
                    x INTEGER NOT NULL,
                    y INTEGER NOT NULL,
                    offset INTEGER NOT NULL,
                    size INTEGER NOT NULL,
                    flags INTEGER NOT NULL,
                    async_id INTEGER NOT NULL,
                    FOREIGN KEY (wdt_id) REFERENCES wdt_files (id),
                    UNIQUE (wdt_id, x, y)
                )
            """)
            
            # Chunk offsets
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS chunk_offsets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wdt_id INTEGER NOT NULL,
                    chunk_name TEXT NOT NULL,
                    offset INTEGER NOT NULL,
                    size INTEGER NOT NULL,
                    data_offset INTEGER NOT NULL,
                    FOREIGN KEY (wdt_id) REFERENCES wdt_files (id)
                )
            """)
            
            # M2 models
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS m2_models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wdt_id INTEGER NOT NULL,
                    x INTEGER NOT NULL,
                    y INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    format TEXT NOT NULL,
                    FOREIGN KEY (wdt_id) REFERENCES wdt_files (id)
                )
            """)
            
            # WMO models
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS wmo_models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wdt_id INTEGER NOT NULL,
                    x INTEGER NOT NULL,
                    y INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    format TEXT NOT NULL,
                    FOREIGN KEY (wdt_id) REFERENCES wdt_files (id)
                )
            """)
            
            # Height maps
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS height_maps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wdt_id INTEGER NOT NULL,
                    x INTEGER NOT NULL,
                    y INTEGER NOT NULL,
                    height_data BLOB NOT NULL,  -- Binary height data
                    grid_size INTEGER NOT NULL,
                    min_height REAL NOT NULL,
                    max_height REAL NOT NULL,
                    avg_height REAL NOT NULL,
                    FOREIGN KEY (wdt_id) REFERENCES wdt_files (id),
                    UNIQUE (wdt_id, x, y)
                )
            """)
            
            # Tile layers
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS tile_layers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wdt_id INTEGER NOT NULL,
                    x INTEGER NOT NULL,
                    y INTEGER NOT NULL,
                    texture_id INTEGER NOT NULL,
                    flags INTEGER NOT NULL,
                    mcal_offset INTEGER NOT NULL,
                    FOREIGN KEY (wdt_id) REFERENCES wdt_files (id)
                )
            """)
            
            # Textures
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS textures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wdt_id INTEGER NOT NULL,
                    x INTEGER NOT NULL,
                    y INTEGER NOT NULL,
                    path TEXT NOT NULL,
                    layer_index INTEGER NOT NULL,
                    blend_mode INTEGER NOT NULL,
                    has_alpha BOOLEAN NOT NULL,
                    is_compressed BOOLEAN NOT NULL,
                    effect_id INTEGER NOT NULL,
                    flags INTEGER NOT NULL,
                    FOREIGN KEY (wdt_id) REFERENCES wdt_files (id)
                )
            """)
            
            # MCNK info
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS tile_mcnk (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wdt_id INTEGER NOT NULL,
                    x INTEGER NOT NULL,
                    y INTEGER NOT NULL,
                    flags INTEGER NOT NULL,
                    area_id INTEGER NOT NULL,
                    n_layers INTEGER NOT NULL,
                    n_doodad_refs INTEGER NOT NULL,
                    holes INTEGER NOT NULL,
                    mcvt_offset INTEGER NOT NULL,
                    mcnr_offset INTEGER NOT NULL,
                    mcly_offset INTEGER NOT NULL,
                    mcrf_offset INTEGER NOT NULL,
                    mcal_offset INTEGER NOT NULL,
                    mcsh_offset INTEGER NOT NULL,
                    mclq_offset INTEGER NOT NULL,
                    liquid_size INTEGER NOT NULL,
                    is_alpha BOOLEAN NOT NULL,
                    texture_map TEXT NOT NULL,  -- JSON array of texture indices
                    doodad_map TEXT NOT NULL,   -- JSON array of doodad flags
                    position_x REAL NOT NULL,   -- World position X
                    position_y REAL NOT NULL,   -- World position Y
                    position_z REAL NOT NULL,   -- World position Z
                    FOREIGN KEY (wdt_id) REFERENCES wdt_files (id),
                    UNIQUE (wdt_id, x, y),
                    CHECK (x BETWEEN 0 AND 63),
                    CHECK (y BETWEEN 0 AND 63)
                )
            """)
            
            # Liquid data
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS liquid_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tile_mcnk_id INTEGER NOT NULL,
                    liquid_type INTEGER NOT NULL,
                    liquid_data BLOB,  -- Binary liquid data
                    min_height REAL,
                    max_height REAL,
                    FOREIGN KEY (tile_mcnk_id) REFERENCES tile_mcnk(id)
                )
            """)
    
    def insert_wdt_record(self, path: str, map_name: str, version: Optional[int],
                         flags: Optional[int], wmo_only: bool, chunk_order: str,
                         format: str) -> int:
        """Insert WDT file record and return its ID"""
        try:
            with self.conn:
                cursor = self.conn.execute("""
                    INSERT INTO wdt_files (path, map_name, version, flags, wmo_only, chunk_order, format)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (str(path), map_name, version, flags, wmo_only, chunk_order, format))
                return cursor.lastrowid
        except sqlite3.Error as e:
            self.logger.error(f"Failed to insert WDT record: {e}")
            raise DatabaseError("Failed to insert WDT record") from e
    
    def insert_map_tile(self, wdt_id: int, x: int, y: int, offset: int,
                       size: int, flags: int, async_id: int):
        """Insert map tile record"""
        try:
            with self.conn:
                self.conn.execute("""
                    INSERT OR REPLACE INTO map_tiles (wdt_id, x, y, offset, size, flags, async_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (wdt_id, x, y, offset, size, flags, async_id))
        except sqlite3.Error as e:
            self.logger.error(f"Failed to insert map tile: {e}")
            raise DatabaseError("Failed to insert map tile") from e
    
    def insert_chunk_offset(self, wdt_id: int, chunk_name: str, offset: int,
                           size: int, data_offset: int):
        """Insert chunk offset record"""
        try:
            with self.conn:
                self.conn.execute("""
                    INSERT INTO chunk_offsets (wdt_id, chunk_name, offset, size, data_offset)
                    VALUES (?, ?, ?, ?, ?)
                """, (wdt_id, chunk_name, offset, size, data_offset))
        except sqlite3.Error as e:
            self.logger.error(f"Failed to insert chunk offset: {e}")
            raise DatabaseError("Failed to insert chunk offset") from e
    
    def insert_m2_model(self, wdt_id: int, x: int, y: int, name: str, format: str):
        """Insert M2 model record"""
        try:
            with self.conn:
                self.conn.execute("""
                    INSERT INTO m2_models (wdt_id, x, y, name, format)
                    VALUES (?, ?, ?, ?, ?)
                """, (wdt_id, x, y, name, format))
        except sqlite3.Error as e:
            self.logger.error(f"Failed to insert M2 model: {e}")
            raise DatabaseError("Failed to insert M2 model") from e
    
    def insert_wmo_model(self, wdt_id: int, x: int, y: int, name: str, format: str):
        """Insert WMO model record"""
        try:
            with self.conn:
                self.conn.execute("""
                    INSERT INTO wmo_models (wdt_id, x, y, name, format)
                    VALUES (?, ?, ?, ?, ?)
                """, (wdt_id, x, y, name, format))
        except sqlite3.Error as e:
            self.logger.error(f"Failed to insert WMO model: {e}")
            raise DatabaseError("Failed to insert WMO model") from e
    
    def insert_height_map(self, wdt_id: int, x: int, y: int,
                         height_data: bytes, grid_size: int,
                         min_height: float, max_height: float, avg_height: float):
        """Insert height map record with binary data"""
        try:
            with self.conn:
                self.conn.execute("""
                    INSERT OR REPLACE INTO height_maps
                    (wdt_id, x, y, height_data, grid_size, min_height, max_height, avg_height)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (wdt_id, x, y, height_data, grid_size, min_height, max_height, avg_height))
        except sqlite3.Error as e:
            self.logger.error(f"Failed to insert height map: {e}")
            raise DatabaseError("Failed to insert height map") from e
    
    def insert_tile_layer(self, wdt_id: int, x: int, y: int, texture_id: int,
                         flags: int, mcal_offset: int):
        """Insert tile layer record"""
        with self.conn:
            self.conn.execute("""
                INSERT INTO tile_layers (wdt_id, x, y, texture_id, flags, mcal_offset)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (wdt_id, x, y, texture_id, flags, mcal_offset))
    
    def insert_texture(self, wdt_id: int, x: int, y: int, path: str,
                      layer_index: int, blend_mode: int, has_alpha: bool,
                      is_compressed: bool, effect_id: int, flags: int):
        """Insert texture record"""
        with self.conn:
            self.conn.execute("""
                INSERT INTO textures (wdt_id, x, y, path, layer_index, blend_mode,
                                    has_alpha, is_compressed, effect_id, flags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (wdt_id, x, y, path, layer_index, blend_mode, has_alpha,
                 is_compressed, effect_id, flags))
    
    def insert_tile_mcnk(self, wdt_id: int, x: int, y: int, header: MCNKHeader) -> int:
        """Insert MCNK info record and return its ID"""
        with self.conn:
            cursor = self.conn.execute("""
                INSERT OR REPLACE INTO tile_mcnk
                (wdt_id, x, y, flags, area_id, n_layers, n_doodad_refs, holes,
                 mcvt_offset, mcnr_offset, mcly_offset, mcrf_offset,
                 mcal_offset, mcsh_offset, mclq_offset, liquid_size, is_alpha,
                 texture_map, doodad_map, position_x, position_y, position_z)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                wdt_id, x, y, int(header.flags), header.area_id, header.n_layers,
                header.n_doodad_refs, header.holes_low_res,
                header.ofs_height or 0, header.ofs_normal or 0, header.ofs_layer,
                header.ofs_refs, header.ofs_alpha, header.ofs_shadow, header.ofs_liquid,
                header.size_liquid, isinstance(header, AlphaMCNKHeader),
                json.dumps(header.low_quality_texture_map),
                json.dumps(header.no_effect_doodad),
                header.position[0], header.position[1], header.position[2]
            ))
            return cursor.lastrowid
    
    def insert_liquid_data(self, tile_mcnk_id: int, liquid_type: int,
                         liquid_data: Optional[bytes], min_height: Optional[float],
                         max_height: Optional[float]):
        """Insert liquid data record with binary data"""
        with self.conn:
            self.conn.execute("""
                INSERT INTO liquid_data
                (tile_mcnk_id, liquid_type, liquid_data, min_height, max_height)
                VALUES (?, ?, ?, ?, ?)
            """, (tile_mcnk_id, liquid_type, liquid_data, min_height, max_height))
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None