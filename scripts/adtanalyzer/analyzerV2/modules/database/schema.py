"""
SQLite database schema for WoW terrain data.
Provides schema definition and initialization functions.
"""
import sqlite3
from typing import Optional
from pathlib import Path

SCHEMA_VERSION = '2.0.0'

def init_database(db_path: Path) -> sqlite3.Connection:
    """
    Initialize SQLite database with schema
    
    Args:
        db_path: Path to database file
        
    Returns:
        Database connection
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.executescript("""
        -- Schema version tracking
        CREATE TABLE IF NOT EXISTS schema_info (
            version TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Base file information
        CREATE TABLE IF NOT EXISTS terrain_files (
            id INTEGER PRIMARY KEY,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,  -- 'adt' or 'wdt'
            format_type TEXT NOT NULL,  -- 'alpha' or 'retail'
            map_name TEXT NOT NULL,
            version INTEGER,
            flags INTEGER,
            chunk_order TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(filename, file_type)
        );
        
        -- Map tiles from WDT
        CREATE TABLE IF NOT EXISTS map_tiles (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL,
            coord_x INTEGER NOT NULL,
            coord_y INTEGER NOT NULL,
            offset INTEGER,
            size INTEGER,
            flags INTEGER,
            async_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(file_id) REFERENCES terrain_files(id)
        );
        
        -- Textures
        CREATE TABLE IF NOT EXISTS textures (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL,
            tile_x INTEGER NOT NULL,
            tile_y INTEGER NOT NULL,
            filename TEXT NOT NULL,
            layer_index INTEGER,
            blend_mode INTEGER,
            has_alpha INTEGER,
            is_compressed INTEGER,
            effect_id INTEGER,
            flags INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(file_id) REFERENCES terrain_files(id)
        );
        
        -- Texture layers (MCLY)
        CREATE TABLE IF NOT EXISTS texture_layers (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL,
            mcnk_index_x INTEGER NOT NULL,
            mcnk_index_y INTEGER NOT NULL,
            texture_id INTEGER NOT NULL,
            flags INTEGER NOT NULL,
            effect_id INTEGER,  -- NULL if no effect
            layer_index INTEGER NOT NULL,
            blend_mode INTEGER NOT NULL,
            is_compressed INTEGER NOT NULL,  -- Boolean
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(file_id) REFERENCES terrain_files(id),
            FOREIGN KEY(texture_id) REFERENCES textures(id)
        );
        
        -- Alpha maps (MCAL)
        CREATE TABLE IF NOT EXISTS alpha_maps (
            id INTEGER PRIMARY KEY,
            layer_id INTEGER NOT NULL,
            alpha_data BLOB NOT NULL,  -- Compressed alpha values
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(layer_id) REFERENCES texture_layers(id)
        );
        
        -- Models
        CREATE TABLE IF NOT EXISTS models (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL,
            model_type TEXT NOT NULL,  -- 'M2' or 'WMO'
            filename TEXT NOT NULL,
            format_type TEXT NOT NULL,  -- 'alpha' or 'retail'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(file_id) REFERENCES terrain_files(id)
        );
        
        -- M2 model placements
        CREATE TABLE IF NOT EXISTS m2_placements (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL,
            tile_x INTEGER NOT NULL,
            tile_y INTEGER NOT NULL,
            unique_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            pos_x REAL NOT NULL,
            pos_y REAL NOT NULL,
            pos_z REAL NOT NULL,
            rot_x REAL NOT NULL,
            rot_y REAL NOT NULL,
            rot_z REAL NOT NULL,
            scale REAL NOT NULL,
            flags INTEGER NOT NULL,
            model_type TEXT NOT NULL DEFAULT 'M2',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(file_id) REFERENCES terrain_files(id)
        );
        
        -- WMO model placements
        CREATE TABLE IF NOT EXISTS wmo_placements (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL,
            tile_x INTEGER NOT NULL,
            tile_y INTEGER NOT NULL,
            unique_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            pos_x REAL NOT NULL,
            pos_y REAL NOT NULL,
            pos_z REAL NOT NULL,
            rot_x REAL NOT NULL,
            rot_y REAL NOT NULL,
            rot_z REAL NOT NULL,
            scale REAL NOT NULL,
            flags INTEGER NOT NULL,
            doodad_set INTEGER,
            name_set INTEGER,
            bounds_min_x REAL,
            bounds_min_y REAL,
            bounds_min_z REAL,
            bounds_max_x REAL,
            bounds_max_y REAL,
            bounds_max_z REAL,
            model_type TEXT NOT NULL DEFAULT 'WMO',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(file_id) REFERENCES terrain_files(id)
        );
        
        -- MCNK data
        CREATE TABLE IF NOT EXISTS mcnk_data (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL,
            tile_x INTEGER NOT NULL,
            tile_y INTEGER NOT NULL,
            index_x INTEGER NOT NULL,
            index_y INTEGER NOT NULL,
            flags INTEGER NOT NULL,
            area_id INTEGER NOT NULL,
            holes INTEGER NOT NULL,
            liquid_type INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(file_id) REFERENCES terrain_files(id)
        );
        
        -- Height maps
        CREATE TABLE IF NOT EXISTS height_maps (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL,
            tile_x INTEGER NOT NULL,
            tile_y INTEGER NOT NULL,
            heights BLOB NOT NULL,  -- Compressed float array
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(file_id) REFERENCES terrain_files(id)
        );
        
        -- Normal data (MCNR)
        CREATE TABLE IF NOT EXISTS normal_data (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL,
            tile_x INTEGER NOT NULL,
            tile_y INTEGER NOT NULL,
            normals BLOB NOT NULL,  -- Compressed float array
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(file_id) REFERENCES terrain_files(id)
        );
        
        -- Liquid data
        CREATE TABLE IF NOT EXISTS liquid_data (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL,
            tile_x INTEGER NOT NULL,
            tile_y INTEGER NOT NULL,
            heights BLOB NOT NULL,  -- Compressed float array
            flags BLOB,  -- Compressed int array
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(file_id) REFERENCES terrain_files(id)
        );
        
        -- Chunk offsets
        CREATE TABLE IF NOT EXISTS chunk_offsets (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL,
            chunk_name TEXT NOT NULL,
            offset INTEGER NOT NULL,
            size INTEGER NOT NULL,
            data_offset INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(file_id) REFERENCES terrain_files(id)
        );
        
        -- Indexes for better query performance
        CREATE INDEX IF NOT EXISTS idx_terrain_files_type ON terrain_files(file_type);
        CREATE INDEX IF NOT EXISTS idx_map_tiles_coords ON map_tiles(coord_x, coord_y);
        CREATE INDEX IF NOT EXISTS idx_textures_file ON textures(file_id);
        CREATE INDEX IF NOT EXISTS idx_texture_layers_file ON texture_layers(file_id);
        CREATE INDEX IF NOT EXISTS idx_models_type ON models(model_type);
        CREATE INDEX IF NOT EXISTS idx_m2_placements_coords ON m2_placements(tile_x, tile_y);
        CREATE INDEX IF NOT EXISTS idx_wmo_placements_coords ON wmo_placements(tile_x, tile_y);
        CREATE INDEX IF NOT EXISTS idx_mcnk_data_coords ON mcnk_data(tile_x, tile_y);
        CREATE INDEX IF NOT EXISTS idx_height_maps_coords ON height_maps(tile_x, tile_y);
        CREATE INDEX IF NOT EXISTS idx_normal_data_coords ON normal_data(tile_x, tile_y);
        CREATE INDEX IF NOT EXISTS idx_liquid_data_coords ON liquid_data(tile_x, tile_y);
    """)
    
    # Store schema version
    c.execute("INSERT INTO schema_info (version) VALUES (?)", (SCHEMA_VERSION,))
    
    conn.commit()
    return conn