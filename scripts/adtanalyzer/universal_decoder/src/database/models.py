"""
SQLite database models for WoW map data
"""

import sqlite3
from typing import List, Dict, Any

class DatabaseManager:
    """Manages SQLite database connection and schema"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self.setup_database()

    def setup_database(self):
        """Create database and tables"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")
        
        # Create tables
        self._create_tables()
        self._create_views()
        self._create_indexes()
        
        self.conn.commit()

    def _create_tables(self):
        """Create all database tables"""
        # Maps table with chunk order tracking
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS maps (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            format TEXT NOT NULL CHECK(format IN ('ALPHA', 'RETAIL')),
            version INTEGER NOT NULL,
            flags INTEGER NOT NULL,
            chunk_order TEXT NOT NULL DEFAULT '',
            UNIQUE(name, format)
        )
        """)
        
        # Map tiles table with version tracking
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS map_tiles (
            id INTEGER PRIMARY KEY,
            map_id INTEGER NOT NULL,
            x INTEGER NOT NULL CHECK(x >= 0 AND x < 64),
            y INTEGER NOT NULL CHECK(y >= 0 AND y < 64),
            flags INTEGER NOT NULL,
            has_data BOOLEAN NOT NULL,
            adt_file TEXT,
            offset INTEGER,
            size INTEGER,
            async_id INTEGER,
            version INTEGER NOT NULL DEFAULT 0,
            header_flags INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (map_id) REFERENCES maps(id) ON DELETE CASCADE,
            UNIQUE (map_id, x, y)
        )
        """)
        
        # Textures table
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS textures (
            id INTEGER PRIMARY KEY,
            map_id INTEGER NOT NULL,
            path TEXT NOT NULL,
            FOREIGN KEY (map_id) REFERENCES maps(id),
            UNIQUE (map_id, path)
        )
        """)
        
        # M2 models table
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS models_m2 (
            id INTEGER PRIMARY KEY,
            map_id INTEGER NOT NULL,
            path TEXT NOT NULL,
            FOREIGN KEY (map_id) REFERENCES maps(id),
            UNIQUE (map_id, path)
        )
        """)
        
        # WMO models table
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS models_wmo (
            id INTEGER PRIMARY KEY,
            map_id INTEGER NOT NULL,
            path TEXT NOT NULL,
            FOREIGN KEY (map_id) REFERENCES maps(id),
            UNIQUE (map_id, path)
        )
        """)
        
        # M2 model placements table
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS model_placements_m2 (
            id INTEGER PRIMARY KEY,
            map_id INTEGER NOT NULL,
            model_id INTEGER NOT NULL,
            unique_id INTEGER NOT NULL,
            pos_x REAL NOT NULL,
            pos_y REAL NOT NULL,
            pos_z REAL NOT NULL,
            rot_x REAL NOT NULL,
            rot_y REAL NOT NULL,
            rot_z REAL NOT NULL,
            scale REAL NOT NULL,
            flags INTEGER NOT NULL,
            FOREIGN KEY (map_id) REFERENCES maps(id),
            FOREIGN KEY (model_id) REFERENCES models_m2(id),
            UNIQUE (map_id, unique_id)
        )
        """)
        
        # WMO model placements table with bounds
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS model_placements_wmo (
            id INTEGER PRIMARY KEY,
            map_id INTEGER NOT NULL,
            model_id INTEGER NOT NULL,
            unique_id INTEGER NOT NULL,
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
            FOREIGN KEY (map_id) REFERENCES maps(id),
            FOREIGN KEY (model_id) REFERENCES models_wmo(id),
            UNIQUE (map_id, unique_id)
        )
        """)
        
        # Terrain chunks table
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS terrain_chunks (
            id INTEGER PRIMARY KEY,
            map_id INTEGER NOT NULL,
            tile_id INTEGER NOT NULL,
            index_x INTEGER NOT NULL CHECK(index_x >= 0 AND index_x < 16),
            index_y INTEGER NOT NULL CHECK(index_y >= 0 AND index_y < 16),
            flags INTEGER NOT NULL,
            area_id INTEGER,
            holes INTEGER,
            has_mcvt BOOLEAN NOT NULL DEFAULT 0,
            has_mcnr BOOLEAN NOT NULL DEFAULT 0,
            has_mclq BOOLEAN NOT NULL DEFAULT 0,
            FOREIGN KEY (map_id) REFERENCES maps(id),
            FOREIGN KEY (tile_id) REFERENCES map_tiles(id),
            UNIQUE (tile_id, index_x, index_y)
        )
        """)
        
        # Terrain heights table
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS terrain_heights (
            id INTEGER PRIMARY KEY,
            chunk_id INTEGER NOT NULL,
            vertex_index INTEGER NOT NULL CHECK(vertex_index >= 0 AND vertex_index < 145),
            height REAL NOT NULL,
            FOREIGN KEY (chunk_id) REFERENCES terrain_chunks(id),
            UNIQUE (chunk_id, vertex_index)
        )
        """)
        
        # Terrain normals table
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS terrain_normals (
            id INTEGER PRIMARY KEY,
            chunk_id INTEGER NOT NULL,
            vertex_index INTEGER NOT NULL CHECK(vertex_index >= 0 AND vertex_index < 145),
            x REAL NOT NULL,
            y REAL NOT NULL,
            z REAL NOT NULL,
            FOREIGN KEY (chunk_id) REFERENCES terrain_chunks(id),
            UNIQUE (chunk_id, vertex_index)
        )
        """)
        
        # Terrain layers table
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS terrain_layers (
            id INTEGER PRIMARY KEY,
            chunk_id INTEGER NOT NULL,
            texture_id INTEGER NOT NULL,
            flags INTEGER NOT NULL,
            effect_id INTEGER,
            offset_in_mcal INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (chunk_id) REFERENCES terrain_chunks(id),
            FOREIGN KEY (texture_id) REFERENCES textures(id)
        )
        """)
        
        # Terrain shadows table
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS terrain_shadows (
            id INTEGER PRIMARY KEY,
            chunk_id INTEGER NOT NULL,
            data BLOB NOT NULL,
            FOREIGN KEY (chunk_id) REFERENCES terrain_chunks(id)
        )
        """)
        
        # Terrain liquid table
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS terrain_liquid (
            id INTEGER PRIMARY KEY,
            chunk_id INTEGER NOT NULL,
            type INTEGER NOT NULL,
            min_height REAL,
            max_height REAL,
            data BLOB,
            FOREIGN KEY (chunk_id) REFERENCES terrain_chunks(id)
        )
        """)

        # Terrain vertex colors table (MCCV)
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS terrain_vertex_colors (
            id INTEGER PRIMARY KEY,
            chunk_id INTEGER NOT NULL,
            vertex_index INTEGER NOT NULL CHECK(vertex_index >= 0 AND vertex_index < 145),
            r INTEGER NOT NULL CHECK(r >= 0 AND r <= 255),
            g INTEGER NOT NULL CHECK(g >= 0 AND g <= 255),
            b INTEGER NOT NULL CHECK(b >= 0 AND b <= 255),
            a INTEGER NOT NULL CHECK(a >= 0 AND a <= 255),
            FOREIGN KEY (chunk_id) REFERENCES terrain_chunks(id),
            UNIQUE (chunk_id, vertex_index)
        )
        """)

        # Terrain alpha maps table (MCAL)
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS terrain_alpha_maps (
            id INTEGER PRIMARY KEY,
            chunk_id INTEGER NOT NULL,
            data BLOB NOT NULL,
            is_compressed BOOLEAN NOT NULL DEFAULT 0,
            FOREIGN KEY (chunk_id) REFERENCES terrain_chunks(id)
        )
        """)

        # Missing files tracking table
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS missing_files (
            id INTEGER PRIMARY KEY,
            map_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            reference_file TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (map_id) REFERENCES maps(id),
            UNIQUE (map_id, file_path)
        )
        """)

    def _create_views(self):
        """Create database views"""
        # Active tiles view
        self.conn.execute("""
        CREATE VIEW IF NOT EXISTS active_tiles AS
        SELECT 
            mt.*,
            m.name as map_name,
            m.format as map_format
        FROM map_tiles mt
        JOIN maps m ON mt.map_id = m.id
        WHERE mt.has_data = 1
        """)
        
        # Model placements view
        self.conn.execute("""
        CREATE VIEW IF NOT EXISTS model_placements AS
        SELECT 
            'M2' as model_type,
            mp.*,
            m2.path as model_path
        FROM model_placements_m2 mp
        JOIN models_m2 m2 ON mp.model_id = m2.id
        UNION ALL
        SELECT 
            'WMO' as model_type,
            mp.*,
            wmo.path as model_path
        FROM model_placements_wmo mp
        JOIN models_wmo wmo ON mp.model_id = wmo.id
        """)

    def _create_indexes(self):
        """Create database indexes"""
        self.conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_map_tiles_coords 
        ON map_tiles(map_id, x, y)
        """)
        
        self.conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_terrain_chunks_location 
        ON terrain_chunks(tile_id, index_x, index_y)
        """)
        
        self.conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_model_placements_m2_map 
        ON model_placements_m2(map_id)
        """)
        
        self.conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_model_placements_wmo_map 
        ON model_placements_wmo(map_id)
        """)

        self.conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_missing_files_map
        ON missing_files(map_id)
        """)

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None