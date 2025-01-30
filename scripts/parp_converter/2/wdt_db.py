import sqlite3
import logging

def setup_database(db_path):
    """Setup SQLite database for WDT analysis"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS wdt_files (
        id INTEGER PRIMARY KEY,
        filename TEXT,
        map_name TEXT,
        version INTEGER,
        flags INTEGER,
        is_wmo_based INTEGER,
        chunk_order TEXT,
        original_format TEXT
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chunk_offsets (
        id INTEGER PRIMARY KEY,
        wdt_id INTEGER,
        chunk_name TEXT,
        offset INTEGER,
        size INTEGER,
        data_offset INTEGER,
        FOREIGN KEY(wdt_id) REFERENCES wdt_files(id)
    )''')

    cursor.execute('''
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
    )''')

    cursor.execute('''
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
    )''')

    cursor.execute('''
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
        mcmt_offset INTEGER,
        mclq_offset INTEGER,
        FOREIGN KEY(wdt_id) REFERENCES wdt_files(id)
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tile_layers (
        id INTEGER PRIMARY KEY,
        tile_mcnk_id INTEGER,
        layer_index INTEGER,
        texture_id INTEGER,
        flags INTEGER,
        effect_id INTEGER,
        FOREIGN KEY(tile_mcnk_id) REFERENCES tile_mcnk(id),
        FOREIGN KEY(texture_id) REFERENCES wdt_textures(id)
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS wdt_textures (
        id INTEGER PRIMARY KEY,
        wdt_id INTEGER,
        tile_x INTEGER,
        tile_y INTEGER,
        texture_path TEXT,
        layer_index INTEGER,
        FOREIGN KEY(wdt_id) REFERENCES wdt_files(id)
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS m2_models (
        id INTEGER PRIMARY KEY,
        wdt_id INTEGER,
        tile_x INTEGER,
        tile_y INTEGER,
        model_path TEXT,
        original_format TEXT,
        FOREIGN KEY(wdt_id) REFERENCES wdt_files(id)
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS wmo_models (
        id INTEGER PRIMARY KEY,
        wdt_id INTEGER,
        tile_x INTEGER,
        tile_y INTEGER,
        model_path TEXT,
        original_format TEXT,
        FOREIGN KEY(wdt_id) REFERENCES wdt_files(id)
    )''')

    cursor.execute('''
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
    )''')

    cursor.execute('''
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
    )''')

    conn.commit()
    return conn

def setup_tile_database(db_path):
    """Setup SQLite database for tile-specific data"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables for tile-level data
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tile_info (
        id INTEGER PRIMARY KEY,
        x INTEGER,
        y INTEGER,
        flags INTEGER,
        offset INTEGER,
        size INTEGER
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS raw_chunks (
        id INTEGER PRIMARY KEY,
        name TEXT,
        offset INTEGER,
        size INTEGER,
        data BLOB
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tile_mcnk (
        id INTEGER PRIMARY KEY,
        flags INTEGER,
        layers INTEGER,
        doodad_refs INTEGER,
        mcvt_offset INTEGER,
        mcnr_offset INTEGER,
        mcly_offset INTEGER,
        mcrf_offset INTEGER,
        mcal_offset INTEGER,
        mcsh_offset INTEGER,
        mcmt_offset INTEGER,
        mclq_offset INTEGER
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tile_layers (
        id INTEGER PRIMARY KEY,
        tile_mcnk_id INTEGER,
        layer_index INTEGER,
        texture_id INTEGER,
        flags INTEGER,
        effect_id INTEGER,
        FOREIGN KEY(tile_mcnk_id) REFERENCES tile_mcnk(id),
        FOREIGN KEY(texture_id) REFERENCES textures(id)
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS textures (
        id INTEGER PRIMARY KEY,
        path TEXT UNIQUE
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS m2_models (
        id INTEGER PRIMARY KEY,
        path TEXT UNIQUE
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS wmo_models (
        id INTEGER PRIMARY KEY,
        path TEXT UNIQUE
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS m2_placements (
        id INTEGER PRIMARY KEY,
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
        FOREIGN KEY(model_id) REFERENCES m2_models(id)
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS wmo_placements (
        id INTEGER PRIMARY KEY,
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
        FOREIGN KEY(model_id) REFERENCES wmo_models(id)
    )''')

    conn.commit()
    return conn

def insert_wdt_record(conn, filename, map_name, version, flags, is_wmo_based=False, chunk_order=None, original_format=None):
    """Insert WDT file record with format information"""
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO wdt_files (filename, map_name, version, flags, is_wmo_based, chunk_order, original_format)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (filename, map_name, version, flags, is_wmo_based, chunk_order, original_format))
    conn.commit()
    return cursor.lastrowid

def insert_chunk_offset(conn, wdt_id, chunk_name, offset, size, data_offset):
    """Insert chunk offset information"""
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO chunk_offsets (wdt_id, chunk_name, offset, size, data_offset)
    VALUES (?, ?, ?, ?, ?)
    ''', (wdt_id, chunk_name, offset, size, data_offset))
    conn.commit()
    return cursor.lastrowid

def insert_adt_offsets(conn, wdt_id, tile_x, tile_y, offsets):
    """Insert ADT chunk offset information"""
    cursor = conn.cursor()
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
    conn.commit()
    return cursor.lastrowid

def insert_map_tile(conn, wdt_id, x, y, offset, size, flags, async_id):
    """Insert map tile record"""
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO map_tiles (wdt_id, tile_x, tile_y, offset, size, flags, async_id)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (wdt_id, x, y, offset, size, flags, async_id))
    conn.commit()
    return cursor.lastrowid

def insert_tile_mcnk(conn, wdt_id, tile_x, tile_y, mcnk_data):
    """Insert MCNK data for a specific tile"""
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO tile_mcnk (
        wdt_id, tile_x, tile_y, flags, layers, doodad_refs,
        mcvt_offset, mcnr_offset, mcly_offset, mcrf_offset,
        mcal_offset, mcsh_offset, mcmt_offset, mclq_offset
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        wdt_id, tile_x, tile_y,
        mcnk_data.flags, mcnk_data.n_layers, mcnk_data.n_doodad_refs,
        mcnk_data.mcvt_offset, mcnk_data.mcnr_offset, mcnk_data.mcly_offset,
        mcnk_data.mcrf_offset, mcnk_data.mcal_offset, mcnk_data.mcsh_offset,
        mcnk_data.mcmt_offset, mcnk_data.mclq_offset
    ))
    conn.commit()
    return cursor.lastrowid

def insert_tile_layer(conn, tile_mcnk_id, layer_index, texture_id, flags, effect_id):
    """Insert layer data for a tile"""
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO tile_layers (tile_mcnk_id, layer_index, texture_id, flags, effect_id)
    VALUES (?, ?, ?, ?, ?)
    ''', (tile_mcnk_id, layer_index, texture_id, flags, effect_id))
    conn.commit()
    return cursor.lastrowid

def insert_texture(conn, wdt_id, tile_x, tile_y, texture_path, layer_index):
    """Insert texture record with tile coordinates"""
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO wdt_textures (wdt_id, tile_x, tile_y, texture_path, layer_index)
    VALUES (?, ?, ?, ?, ?)
    ''', (wdt_id, tile_x, tile_y, texture_path, layer_index))
    conn.commit()
    return cursor.lastrowid

def insert_m2_model(conn, wdt_id, tile_x, tile_y, model_path, original_format=None):
    """Insert M2 model record with tile coordinates"""
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO m2_models (wdt_id, tile_x, tile_y, model_path, original_format)
    VALUES (?, ?, ?, ?, ?)
    ''', (wdt_id, tile_x, tile_y, model_path, original_format))
    conn.commit()
    return cursor.lastrowid

def insert_wmo_model(conn, wdt_id, tile_x, tile_y, model_path, original_format=None):
    """Insert WMO model record with tile coordinates"""
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO wmo_models (wdt_id, tile_x, tile_y, model_path, original_format)
    VALUES (?, ?, ?, ?, ?)
    ''', (wdt_id, tile_x, tile_y, model_path, original_format))
    conn.commit()
    return cursor.lastrowid

def insert_m2_placement(conn, wdt_id, tile_x, tile_y, model_id, unique_id, position, rotation, scale, flags):
    """Insert M2 placement record with tile coordinates"""
    cursor = conn.cursor()
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
    conn.commit()
    return cursor.lastrowid

def insert_wmo_placement(conn, wdt_id, tile_x, tile_y, model_id, unique_id, position, rotation, scale, flags,
                        doodad_set, name_set, bounds_min, bounds_max):
    """Insert WMO placement record with tile coordinates"""
    cursor = conn.cursor()
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
    conn.commit()
    return cursor.lastrowid

# Functions for tile-specific operations
def insert_raw_chunk(conn, chunk_name, offset, size, data):
    """Insert raw chunk data into tile database"""
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO raw_chunks (name, offset, size, data)
    VALUES (?, ?, ?, ?)
    ''', (chunk_name, offset, size, data))
    conn.commit()
    return cursor.lastrowid

def insert_tile_texture(conn, texture_path):
    """Insert texture into tile database"""
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR IGNORE INTO textures (path)
    VALUES (?)
    ''', (texture_path,))
    conn.commit()
    return cursor.lastrowid

def insert_tile_m2_model(conn, model_path):
    """Insert M2 model into tile database"""
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR IGNORE INTO m2_models (path)
    VALUES (?)
    ''', (model_path,))
    conn.commit()
    return cursor.lastrowid

def insert_tile_wmo_model(conn, model_path):
    """Insert WMO model into tile database"""
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR IGNORE INTO wmo_models (path)
    VALUES (?)
    ''', (model_path,))
    conn.commit()
    return cursor.lastrowid

def insert_tile_m2_placement(conn, model_id, unique_id, position, rotation, scale, flags):
    """Insert M2 placement into tile database"""
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO m2_placements (
        model_id, unique_id,
        position_x, position_y, position_z,
        rotation_x, rotation_y, rotation_z,
        scale, flags
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        model_id, unique_id,
        position[0], position[1], position[2],
        rotation[0], rotation[1], rotation[2],
        scale, flags
    ))
    conn.commit()
    return cursor.lastrowid

def insert_tile_wmo_placement(conn, model_id, unique_id, position, rotation, scale, flags,
                            doodad_set, name_set, bounds_min, bounds_max):
    """Insert WMO placement into tile database"""
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO wmo_placements (
        model_id, unique_id,
        position_x, position_y, position_z,
        rotation_x, rotation_y, rotation_z,
        scale, flags, doodad_set, name_set,
        bounds_min_x, bounds_min_y, bounds_min_z,
        bounds_max_x, bounds_max_y, bounds_max_z
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        model_id, unique_id,
        position[0], position[1], position[2],
        rotation[0], rotation[1], rotation[2],
        scale, flags, doodad_set, name_set,
        bounds_min[0], bounds_min[1], bounds_min[2],
        bounds_max[0], bounds_max[1], bounds_max[2]
    ))
    conn.commit()
    return cursor.lastrowid

def insert_tile_mcnk_data(conn, mcnk_data):
    """Insert MCNK data into tile database"""
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO tile_mcnk (
        flags, layers, doodad_refs,
        mcvt_offset, mcnr_offset, mcly_offset, mcrf_offset,
        mcal_offset, mcsh_offset, mcmt_offset, mclq_offset
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        mcnk_data.flags, mcnk_data.n_layers, mcnk_data.n_doodad_refs,
        mcnk_data.mcvt_offset, mcnk_data.mcnr_offset, mcnk_data.mcly_offset,
        mcnk_data.mcrf_offset, mcnk_data.mcal_offset, mcnk_data.mcsh_offset,
        mcnk_data.mcmt_offset, mcnk_data.mclq_offset
    ))
    conn.commit()
    return cursor.lastrowid