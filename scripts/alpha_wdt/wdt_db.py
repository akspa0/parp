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
        blend_mode INTEGER DEFAULT 0,
        has_alpha INTEGER DEFAULT 0,
        is_compressed INTEGER DEFAULT 0,
        effect_id INTEGER DEFAULT 0,
        flags INTEGER DEFAULT 0,
        FOREIGN KEY(wdt_id) REFERENCES wdt_files(id)
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS m2_models (
        id INTEGER PRIMARY KEY,
        wdt_id INTEGER,
        tile_x INTEGER,
        tile_y INTEGER,
        model_path TEXT,
        format_type TEXT,
        FOREIGN KEY(wdt_id) REFERENCES wdt_files(id)
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS wmo_models (
        id INTEGER PRIMARY KEY,
        wdt_id INTEGER,
        tile_x INTEGER,
        tile_y INTEGER,
        model_path TEXT,
        format_type TEXT,
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
    CREATE TABLE IF NOT EXISTS height_map_info (
        id INTEGER PRIMARY KEY,
        tile_mcnk_id INTEGER,
        height_data BLOB,
        grid_size INTEGER DEFAULT 145,  -- 9x9 + 8x8 grid for Alpha
        min_height REAL,
        max_height REAL,
        avg_height REAL,
        FOREIGN KEY(tile_mcnk_id) REFERENCES tile_mcnk(id)
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS liquid_data (
        id INTEGER PRIMARY KEY,
        tile_mcnk_id INTEGER,
        liquid_type INTEGER,  -- 0=none, 1=water, 2=ocean, 3=magma, 4=slime
        liquid_data BLOB,     -- Array of height values
        min_height REAL,
        max_height REAL,
        FOREIGN KEY(tile_mcnk_id) REFERENCES tile_mcnk(id)
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
    """
    Insert MCNK data for a specific tile with enhanced information
    
    Args:
        conn: Database connection
        wdt_id: WDT file ID
        tile_x: Tile X coordinate
        tile_y: Tile Y coordinate
        mcnk_data: Dictionary containing MCNK chunk data with the following structure:
            {
                'flags': int,
                'n_layers': int,
                'n_doodad_refs': int,
                'mcvt_offset': int,
                'mcnr_offset': int,
                'mcly_offset': int,
                'mcrf_offset': int,
                'mcal_offset': int,
                'mcsh_offset': int,
                'mcmt_offset': int,
                'mclq_offset': int,
                'area_id': int,
                'holes': int,
                'liquid': {'size': int},
                'position': {'x': float, 'y': float, 'z': float}
            }
    """
    cursor = conn.cursor()
    
    # Extract position from mcnk_data if available
    position = mcnk_data.get('position', {'x': 0.0, 'y': 0.0, 'z': 0.0})
    liquid = mcnk_data.get('liquid', {'size': 0})
    
    # Check for specific flags
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

def insert_texture(conn, wdt_id, tile_x, tile_y, texture_path, layer_index,
                  blend_mode=0, has_alpha=0, is_compressed=0, effect_id=0, flags=0):
    """
    Insert texture record with enhanced information
    
    Args:
        conn: Database connection
        wdt_id: WDT file ID
        tile_x: Tile X coordinate
        tile_y: Tile Y coordinate
        texture_path: Path to texture file
        layer_index: Layer index (0 for base layer)
        blend_mode: Texture blend mode
        has_alpha: Whether texture has alpha channel
        is_compressed: Whether texture data is compressed
        effect_id: Special effect ID
        flags: Additional texture flags
    """
    cursor = conn.cursor()
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
    conn.commit()
    return cursor.lastrowid

def insert_m2_model(conn, wdt_id, tile_x, tile_y, model_path, format_type):
    """Insert M2 model record"""
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO m2_models (wdt_id, tile_x, tile_y, model_path, format_type)
    VALUES (?, ?, ?, ?, ?)
    ''', (wdt_id, tile_x, tile_y, model_path, format_type))
    conn.commit()
    return cursor.lastrowid

def insert_wmo_model(conn, wdt_id, tile_x, tile_y, model_path, format_type):
    """Insert WMO model record"""
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO wmo_models (wdt_id, tile_x, tile_y, model_path, format_type)
    VALUES (?, ?, ?, ?, ?)
    ''', (wdt_id, tile_x, tile_y, model_path, format_type))
    conn.commit()
    return cursor.lastrowid

def insert_m2_placement(conn, wdt_id, tile_x, tile_y, model_id, unique_id, position, rotation, scale, flags):
    """Insert M2 placement record"""
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

def insert_height_map(conn, tile_mcnk_id, height_data):
    """
    Insert height map data for a tile with enhanced metadata
    Args:
        conn: Database connection
        tile_mcnk_id: ID of the MCNK tile
        height_data: array.array of float height values
    """
    cursor = conn.cursor()
    
    # Calculate height statistics
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
    conn.commit()
    return cursor.lastrowid

def insert_liquid_data(conn, tile_mcnk_id, liquid_type, liquid_heights):
    """
    Insert liquid data for a tile with enhanced metadata
    Args:
        conn: Database connection
        tile_mcnk_id: ID of the MCNK tile
        liquid_type: Type of liquid (0=none, 1=water, 2=ocean, 3=magma, 4=slime)
        liquid_heights: array.array of float height values
    """
    cursor = conn.cursor()
    
    # Calculate height statistics if we have height data
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
    conn.commit()
    return cursor.lastrowid

def insert_wmo_placement(conn, wdt_id, tile_x, tile_y, model_id, unique_id, position, rotation, scale, flags,
                        doodad_set, name_set, bounds_min, bounds_max):
    """Insert WMO placement record"""
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