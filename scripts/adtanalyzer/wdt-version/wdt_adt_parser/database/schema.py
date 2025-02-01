"""
Database schema and setup for WDT/ADT parsing.
Implements the same schema as the original wdt_db.py.
"""
import sqlite3
import logging
from pathlib import Path
from typing import Optional, Tuple, List, Any, Dict

class DatabaseSchema:
    """Database schema definitions and setup"""
    
    TABLES = {
        'wdt_files': '''
        CREATE TABLE IF NOT EXISTS wdt_files (
            id INTEGER PRIMARY KEY,
            filename TEXT,
            map_name TEXT,
            version INTEGER,
            flags INTEGER,
            is_wmo_based INTEGER,
            chunk_order TEXT,
            original_format TEXT
        )''',
        
        'chunk_offsets': '''
        CREATE TABLE IF NOT EXISTS chunk_offsets (
            id INTEGER PRIMARY KEY,
            wdt_id INTEGER,
            chunk_name TEXT,
            offset INTEGER,
            size INTEGER,
            data_offset INTEGER,
            FOREIGN KEY(wdt_id) REFERENCES wdt_files(id)
        )''',
        
        'adt_offsets': '''
        CREATE TABLE IF NOT EXISTS adt_offsets (
            id INTEGER PRIMARY KEY,
            wdt_id INTEGER,
            tile_x INTEGER,
            tile_y INTEGER,
            mhdr_offset INTEGER,
            mcin_offset INTEGER,
            mtex_offset INTEGER,
            mmdx_offset INTEGER,
            mmid_offset INTEGER,
            mwmo_offset INTEGER,
            mwid_offset INTEGER,
            mddf_offset INTEGER,
            modf_offset INTEGER,
            FOREIGN KEY(wdt_id) REFERENCES wdt_files(id)
        )''',
        
        'map_tiles': '''
        CREATE TABLE IF NOT EXISTS map_tiles (
            id INTEGER PRIMARY KEY,
            wdt_id INTEGER,
            tile_x INTEGER,
            tile_y INTEGER,
            offset INTEGER,
            size INTEGER,
            flags INTEGER,
            async_id INTEGER,
            FOREIGN KEY(wdt_id) REFERENCES wdt_files(id)
        )''',
        
        'tile_mcnk': '''
        CREATE TABLE IF NOT EXISTS tile_mcnk (
            id INTEGER PRIMARY KEY,
            wdt_id INTEGER,
            tile_x INTEGER,
            tile_y INTEGER,
            flags INTEGER,
            layers INTEGER,
            doodad_refs INTEGER,
            mcvt_offset INTEGER,
            mcnr_offset INTEGER,
            mcly_offset INTEGER,
            mcrf_offset INTEGER,
            mcal_offset INTEGER,
            mcsh_offset INTEGER,
            mclq_offset INTEGER,
            area_id INTEGER,
            holes INTEGER,
            liquid_size INTEGER,
            position_x REAL,
            position_y REAL,
            position_z REAL,
            has_vertex_colors INTEGER DEFAULT 0,
            has_shadows INTEGER DEFAULT 0,
            FOREIGN KEY(wdt_id) REFERENCES wdt_files(id)
        )''',
        
        'tile_layers': '''
        CREATE TABLE IF NOT EXISTS tile_layers (
            id INTEGER PRIMARY KEY,
            tile_mcnk_id INTEGER,
            layer_index INTEGER,
            texture_id INTEGER,
            flags INTEGER,
            effect_id INTEGER,
            FOREIGN KEY(tile_mcnk_id) REFERENCES tile_mcnk(id),
            FOREIGN KEY(texture_id) REFERENCES wdt_textures(id)
        )''',
        
        'wdt_textures': '''
        CREATE TABLE IF NOT EXISTS wdt_textures (
            id INTEGER PRIMARY KEY,
            wdt_id INTEGER,
            tile_x INTEGER,
            tile_y INTEGER,
            texture_path TEXT,
            layer_index INTEGER,
            blend_mode INTEGER DEFAULT 0,
            has_alpha INTEGER DEFAULT 0,
            is_compressed INTEGER DEFAULT 0,
            effect_id INTEGER DEFAULT 0,
            flags INTEGER DEFAULT 0,
            FOREIGN KEY(wdt_id) REFERENCES wdt_files(id)
        )''',
        
        'm2_models': '''
        CREATE TABLE IF NOT EXISTS m2_models (
            id INTEGER PRIMARY KEY,
            wdt_id INTEGER,
            tile_x INTEGER,
            tile_y INTEGER,
            model_path TEXT,
            format_type TEXT,
            FOREIGN KEY(wdt_id) REFERENCES wdt_files(id)
        )''',
        
        'wmo_models': '''
        CREATE TABLE IF NOT EXISTS wmo_models (
            id INTEGER PRIMARY KEY,
            wdt_id INTEGER,
            tile_x INTEGER,
            tile_y INTEGER,
            model_path TEXT,
            format_type TEXT,
            FOREIGN KEY(wdt_id) REFERENCES wdt_files(id)
        )''',
        
        'm2_placements': '''
        CREATE TABLE IF NOT EXISTS m2_placements (
            id INTEGER PRIMARY KEY,
            wdt_id INTEGER,
            tile_x INTEGER,
            tile_y INTEGER,
            model_id INTEGER,
            unique_id INTEGER,
            position_x REAL,
            position_y REAL,
            position_z REAL,
            rotation_x REAL,
            rotation_y REAL,
            rotation_z REAL,
            scale REAL,
            flags INTEGER,
            FOREIGN KEY(wdt_id) REFERENCES wdt_files(id),
            FOREIGN KEY(model_id) REFERENCES m2_models(id)
        )''',
        
        'height_map_info': '''
        CREATE TABLE IF NOT EXISTS height_map_info (
            id INTEGER PRIMARY KEY,
            tile_mcnk_id INTEGER,
            height_data BLOB,
            grid_size INTEGER DEFAULT 145,  -- 9x9 + 8x8 grid for Alpha
            min_height REAL,
            max_height REAL,
            avg_height REAL,
            FOREIGN KEY(tile_mcnk_id) REFERENCES tile_mcnk(id)
        )''',
        
        'liquid_data': '''
        CREATE TABLE IF NOT EXISTS liquid_data (
            id INTEGER PRIMARY KEY,
            tile_mcnk_id INTEGER,
            liquid_type INTEGER,  -- 0=none, 1=water, 2=ocean, 3=magma, 4=slime
            liquid_data BLOB,     -- Array of height values
            min_height REAL,
            max_height REAL,
            FOREIGN KEY(tile_mcnk_id) REFERENCES tile_mcnk(id)
        )''',
        
        'wmo_placements': '''
        CREATE TABLE IF NOT EXISTS wmo_placements (
            id INTEGER PRIMARY KEY,
            wdt_id INTEGER,
            tile_x INTEGER,
            tile_y INTEGER,
            model_id INTEGER,
            unique_id INTEGER,
            position_x REAL,
            position_y REAL,
            position_z REAL,
            rotation_x REAL,
            rotation_y REAL,
            rotation_z REAL,
            scale REAL,
            flags INTEGER,
            doodad_set INTEGER,
            name_set INTEGER,
            bounds_min_x REAL,
            bounds_min_y REAL,
            bounds_min_z REAL,
            bounds_max_x REAL,
            bounds_max_y REAL,
            bounds_max_z REAL,
            FOREIGN KEY(wdt_id) REFERENCES wdt_files(id),
            FOREIGN KEY(model_id) REFERENCES wmo_models(id)
        )'''
    }
    
    @classmethod
    def setup_database(cls, db_path: Path) -> sqlite3.Connection:
        """
        Set up the database with all required tables
        
        Args:
            db_path: Path to the SQLite database file
            
        Returns:
            SQLite database connection
        """
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Create all tables
        for table_name, create_sql in cls.TABLES.items():
            try:
                cursor.execute(create_sql)
            except sqlite3.Error as e:
                logging.error(f"Error creating table {table_name}: {e}")
                raise
        
        conn.commit()
        return conn