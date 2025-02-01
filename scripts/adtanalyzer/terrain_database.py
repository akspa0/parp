"""
Database handling for WoW terrain files.
Provides unified schema and operations for both ADT and WDT data.
"""
import sqlite3
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path
import logging
import zlib
import array
from terrain_structures import (
    TerrainFile, ADTFile, WDTFile, TextureInfo, ModelReference,
    ModelPlacement, WMOPlacement, MCNKInfo, MapTile, TextureLayer
)

class DatabaseError(Exception):
    """Database operation error"""
    pass

def compress_array(data: List[float]) -> bytes:
    """Compress float array to binary"""
    arr = array.array('f', data)
    return zlib.compress(arr.tobytes())

def decompress_array(data: bytes) -> List[float]:
    """Decompress binary to float array"""
    arr = array.array('f')
    arr.frombytes(zlib.decompress(data))
    return arr.tolist()

def setup_database(db_path: str) -> sqlite3.Connection:
    """Set up SQLite database with unified schema"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.executescript("""
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
            UNIQUE(filename, file_type)
        );
        
        -- Map tiles
        CREATE TABLE IF NOT EXISTS map_tiles (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL,
            coord_x INTEGER NOT NULL,
            coord_y INTEGER NOT NULL,
            offset INTEGER,
            size INTEGER,
            flags INTEGER,
            async_id INTEGER,
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
            effect_id INTEGER,
            layer_index INTEGER NOT NULL,
            blend_mode INTEGER,
            FOREIGN KEY(file_id) REFERENCES terrain_files(id),
            FOREIGN KEY(texture_id) REFERENCES textures(id)
        );
        
        -- Alpha maps (MCAL)
        CREATE TABLE IF NOT EXISTS alpha_maps (
            id INTEGER PRIMARY KEY,
            layer_id INTEGER NOT NULL,
            alpha_data BLOB NOT NULL,  -- Compressed alpha values
            FOREIGN KEY(layer_id) REFERENCES texture_layers(id)
        );
        
        -- Models
        CREATE TABLE IF NOT EXISTS models (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL,
            model_type TEXT NOT NULL,  -- 'M2' or 'WMO'
            filename TEXT NOT NULL,
            format_type TEXT NOT NULL,  -- 'alpha' or 'retail'
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
            FOREIGN KEY(file_id) REFERENCES terrain_files(id)
        );
        
        -- Height maps
        CREATE TABLE IF NOT EXISTS height_maps (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL,
            tile_x INTEGER NOT NULL,
            tile_y INTEGER NOT NULL,
            heights BLOB NOT NULL,  -- Store as compressed binary
            FOREIGN KEY(file_id) REFERENCES terrain_files(id)
        );
        
        -- Liquid data
        CREATE TABLE IF NOT EXISTS liquid_data (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL,
            tile_x INTEGER NOT NULL,
            tile_y INTEGER NOT NULL,
            heights BLOB NOT NULL,  -- Store as compressed binary
            flags BLOB,  -- Store as compressed binary
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
            FOREIGN KEY(file_id) REFERENCES terrain_files(id)
        );
    """)
    
    conn.commit()
    return conn

def insert_terrain_file(conn: sqlite3.Connection, file: TerrainFile) -> int:
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
        int(file.flags),
        ','.join(file.chunk_order)
    ))
    return c.lastrowid

def insert_map_tile(conn: sqlite3.Connection, file_id: int, tile: MapTile) -> int:
    """Insert map tile record"""
    c = conn.cursor()
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
    return c.lastrowid

def insert_texture(conn: sqlite3.Connection, file_id: int, texture: TextureInfo,
                  tile_x: int, tile_y: int) -> int:
    """Insert texture record"""
    c = conn.cursor()
    c.execute("""
        INSERT INTO textures
        (file_id, tile_x, tile_y, filename, layer_index,
         blend_mode, has_alpha, is_compressed, effect_id, flags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        file_id,
        tile_x,
        tile_y,
        texture.filename,
        texture.layer_index,
        texture.blend_mode,
        0,  # has_alpha
        1 if texture.is_compressed else 0,
        texture.effect_id,
        texture.flags
    ))
    return c.lastrowid

def insert_texture_layer(conn: sqlite3.Connection, file_id: int,
                        mcnk_x: int, mcnk_y: int, layer: TextureLayer) -> int:
    """Insert texture layer record"""
    c = conn.cursor()
    c.execute("""
        INSERT INTO texture_layers
        (file_id, mcnk_index_x, mcnk_index_y, texture_id,
         flags, effect_id, layer_index, blend_mode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        file_id,
        mcnk_x,
        mcnk_y,
        layer.texture_id,
        layer.flags,
        layer.effect_id,
        layer.layer_index,
        layer.blend_mode
    ))
    layer_id = c.lastrowid
    
    # Store alpha map if available
    if layer.alpha_map:
        insert_alpha_map(conn, layer_id, layer.alpha_map)
    
    return layer_id

def insert_alpha_map(conn: sqlite3.Connection, layer_id: int, alpha_values: List[int]) -> int:
    """Insert alpha map data"""
    c = conn.cursor()
    c.execute("""
        INSERT INTO alpha_maps
        (layer_id, alpha_data)
        VALUES (?, ?)
    """, (
        layer_id,
        compress_array(alpha_values)
    ))
    return c.lastrowid

def insert_model(conn: sqlite3.Connection, file_id: int, model: ModelReference) -> int:
    """Insert model record"""
    c = conn.cursor()
    c.execute("""
        INSERT INTO models
        (file_id, model_type, filename, format_type)
        VALUES (?, ?, ?, ?)
    """, (
        file_id,
        'M2' if model.path.lower().endswith(('.m2', '.mdx')) else 'WMO',
        model.path,
        model.format_type
    ))
    return c.lastrowid

def insert_m2_placement(conn: sqlite3.Connection, file_id: int, placement: ModelPlacement,
                       filename: str, tile_x: int, tile_y: int) -> int:
    """Insert M2 model placement record"""
    c = conn.cursor()
    c.execute("""
        INSERT INTO m2_placements
        (file_id, tile_x, tile_y, unique_id, filename,
         pos_x, pos_y, pos_z, rot_x, rot_y, rot_z,
         scale, flags, model_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        file_id, tile_x, tile_y,
        placement.unique_id, filename,
        placement.position.x, placement.position.y, placement.position.z,
        placement.rotation.x, placement.rotation.y, placement.rotation.z,
        placement.scale, placement.flags,
        'MDX' if filename.lower().endswith('.mdx') else 'M2'
    ))
    return c.lastrowid

def insert_wmo_placement(conn: sqlite3.Connection, file_id: int, placement: WMOPlacement,
                        filename: str, tile_x: int, tile_y: int) -> int:
    """Insert WMO model placement record"""
    c = conn.cursor()
    c.execute("""
        INSERT INTO wmo_placements
        (file_id, tile_x, tile_y, unique_id, filename,
         pos_x, pos_y, pos_z, rot_x, rot_y, rot_z,
         scale, flags, doodad_set, name_set,
         bounds_min_x, bounds_min_y, bounds_min_z,
         bounds_max_x, bounds_max_y, bounds_max_z,
         model_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        file_id, tile_x, tile_y,
        placement.unique_id, filename,
        placement.position.x, placement.position.y, placement.position.z,
        placement.rotation.x, placement.rotation.y, placement.rotation.z,
        placement.scale, placement.flags,
        placement.doodad_set, placement.name_set,
        placement.bounding_box.min.x, placement.bounding_box.min.y, placement.bounding_box.min.z,
        placement.bounding_box.max.x, placement.bounding_box.max.y, placement.bounding_box.max.z,
        'WMO'
    ))
    return c.lastrowid

def insert_mcnk_data(conn: sqlite3.Connection, file_id: int, mcnk: MCNKInfo,
                    tile_x: int, tile_y: int) -> int:
    """Insert MCNK data record"""
    c = conn.cursor()
    c.execute("""
        INSERT INTO mcnk_data
        (file_id, tile_x, tile_y, index_x, index_y,
         flags, area_id, holes, liquid_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        file_id,
        tile_x,
        tile_y,
        mcnk.index_x,
        mcnk.index_y,
        int(mcnk.flags),
        mcnk.area_id,
        mcnk.holes,
        mcnk.liquid_type
    ))
    return c.lastrowid

def insert_height_map(conn: sqlite3.Connection, file_id: int,
                     tile_x: int, tile_y: int, heights: List[float]) -> int:
    """Insert height map data"""
    c = conn.cursor()
    c.execute("""
        INSERT INTO height_maps
        (file_id, tile_x, tile_y, heights)
        VALUES (?, ?, ?, ?)
    """, (
        file_id,
        tile_x,
        tile_y,
        compress_array(heights)
    ))
    return c.lastrowid

def insert_liquid_data(conn: sqlite3.Connection, file_id: int,
                      tile_x: int, tile_y: int,
                      heights: List[float], flags: Optional[List[int]] = None) -> int:
    """Insert liquid data"""
    c = conn.cursor()
    c.execute("""
        INSERT INTO liquid_data
        (file_id, tile_x, tile_y, heights, flags)
        VALUES (?, ?, ?, ?, ?)
    """, (
        file_id,
        tile_x,
        tile_y,
        compress_array(heights),
        compress_array(flags) if flags else None
    ))
    return c.lastrowid

def insert_chunk_offset(conn: sqlite3.Connection, file_id: int,
                       chunk_name: str, offset: int, size: int, data_offset: int) -> int:
    """Insert chunk offset record"""
    c = conn.cursor()
    c.execute("""
        INSERT INTO chunk_offsets
        (file_id, chunk_name, offset, size, data_offset)
        VALUES (?, ?, ?, ?, ?)
    """, (
        file_id,
        chunk_name,
        offset,
        size,
        data_offset
    ))
    return c.lastrowid