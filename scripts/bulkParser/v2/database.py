"""
Database operations for the ADT Analyzer
Handles database setup, schema, and data insertion operations
"""

import sqlite3
import struct
import logging

logger = logging.getLogger("parser")

def setup_database(db_path):
    """Set up the SQLite database with all necessary tables"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # ADT files table
    c.execute("""
    CREATE TABLE IF NOT EXISTS adt_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        folder_name TEXT,
        x_coord INTEGER,
        y_coord INTEGER,
        version INTEGER
    )
    """)
    
    # Textures table
    c.execute("""
    CREATE TABLE IF NOT EXISTS textures (
        adt_id INTEGER,
        texture TEXT,
        file_data_id INTEGER,
        texture_type TEXT,
        FOREIGN KEY(adt_id) REFERENCES adt_files(id)
    )
    """)
    
    # M2 models table
    c.execute("""
    CREATE TABLE IF NOT EXISTS m2_models (
        adt_id INTEGER,
        model_name TEXT,
        FOREIGN KEY(adt_id) REFERENCES adt_files(id)
    )
    """)
    
    # WMO models table
    c.execute("""
    CREATE TABLE IF NOT EXISTS wmo_models (
        adt_id INTEGER,
        wmo_name TEXT,
        FOREIGN KEY(adt_id) REFERENCES adt_files(id)
    )
    """)
    
    # MDDF table - M2 placement
    c.execute("""
    CREATE TABLE IF NOT EXISTS mddf (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        adt_id INTEGER,
        uniqueId INTEGER,
        model_name TEXT,
        file_data_id INTEGER,
        posX REAL,
        posY REAL,
        posZ REAL,
        rotX REAL,
        rotY REAL,
        rotZ REAL,
        scale REAL,
        flags INTEGER,
        FOREIGN KEY(adt_id) REFERENCES adt_files(id)
    )
    """)
    
    # MODF table - WMO placement
    c.execute("""
    CREATE TABLE IF NOT EXISTS modf (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        adt_id INTEGER,
        uniqueId INTEGER,
        wmo_name TEXT,
        file_data_id INTEGER,
        posX REAL,
        posY REAL,
        posZ REAL,
        rotX REAL,
        rotY REAL,
        rotZ REAL,
        scale REAL,
        flags INTEGER,
        doodadSet INTEGER,
        nameSet INTEGER,
        FOREIGN KEY(adt_id) REFERENCES adt_files(id)
    )
    """)
    
    # MCNK table - Terrain chunks
    c.execute("""
    CREATE TABLE IF NOT EXISTS mcnk (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        adt_id INTEGER,
        index_x INTEGER,
        index_y INTEGER,
        flags INTEGER,
        areaid INTEGER,
        position_x REAL,
        position_y REAL,
        position_z REAL,
        has_mcvt INTEGER,
        has_mcnr INTEGER,
        has_mclq INTEGER,
        has_mcsh INTEGER,
        has_mccv INTEGER,
        has_mclv INTEGER,
        FOREIGN KEY(adt_id) REFERENCES adt_files(id)
    )
    """)
    
    # MCVT table - Height data
    c.execute("""
    CREATE TABLE IF NOT EXISTS mcvt (
        mcnk_id INTEGER,
        heights BLOB,
        FOREIGN KEY(mcnk_id) REFERENCES mcnk(id)
    )
    """)
    
    # MCNR table - Normal data
    c.execute("""
    CREATE TABLE IF NOT EXISTS mcnr (
        mcnk_id INTEGER,
        normals BLOB,
        FOREIGN KEY(mcnk_id) REFERENCES mcnk(id)
    )
    """)
    
    # MCLY table - Layer data
    c.execute("""
    CREATE TABLE IF NOT EXISTS mcly (
        mcnk_id INTEGER,
        textureId INTEGER,
        flags INTEGER,
        offsetInMCAL INTEGER,
        effectId INTEGER,
        FOREIGN KEY(mcnk_id) REFERENCES mcnk(id)
    )
    """)
    
    # MCAL table - Alpha map data
    c.execute("""
    CREATE TABLE IF NOT EXISTS mcal (
        mcnk_id INTEGER,
        alpha_map BLOB,
        compressed INTEGER,
        FOREIGN KEY(mcnk_id) REFERENCES mcnk(id)
    )
    """)
    
    # MCSH table - Shadow map data
    c.execute("""
    CREATE TABLE IF NOT EXISTS mcsh (
        mcnk_id INTEGER,
        shadow_map BLOB,
        FOREIGN KEY(mcnk_id) REFERENCES mcnk(id)
    )
    """)
    
    # MCLQ table - Liquid data
    c.execute("""
    CREATE TABLE IF NOT EXISTS mclq (
        mcnk_id INTEGER,
        liquid_data BLOB,
        FOREIGN KEY(mcnk_id) REFERENCES mcnk(id)
    )
    """)
    
    # MCCV table - Vertex color data
    c.execute("""
    CREATE TABLE IF NOT EXISTS mccv (
        mcnk_id INTEGER,
        vertex_colors BLOB,
        FOREIGN KEY(mcnk_id) REFERENCES mcnk(id)
    )
    """)
    
    # MCLV table - Chunk lighting data (Cata+)
    c.execute("""
    CREATE TABLE IF NOT EXISTS mclv (
        mcnk_id INTEGER,
        lighting_data BLOB,
        FOREIGN KEY(mcnk_id) REFERENCES mcnk(id)
    )
    """)

    # MCMT table - Material IDs (Cata+)
    c.execute("""
    CREATE TABLE IF NOT EXISTS mcmt (
        adt_id INTEGER,
        material_ids BLOB,
        FOREIGN KEY(adt_id) REFERENCES adt_files(id)
    )
    """)
    
    # MAMP table - Alpha map parameters (Cata+)
    c.execute("""
    CREATE TABLE IF NOT EXISTS mamp (
        adt_id INTEGER,
        value INTEGER,
        FOREIGN KEY(adt_id) REFERENCES adt_files(id)
    )
    """)
    
    # MTXF table - Texture flags (WotLK+)
    c.execute("""
    CREATE TABLE IF NOT EXISTS mtxf (
        adt_id INTEGER,
        texture_flags BLOB,
        FOREIGN KEY(adt_id) REFERENCES adt_files(id)
    )
    """)
    
    # MTXP table - Texture parameters (MoP+)
    c.execute("""
    CREATE TABLE IF NOT EXISTS mtxp (
        adt_id INTEGER,
        texture_params BLOB,
        FOREIGN KEY(adt_id) REFERENCES adt_files(id)
    )
    """)
    
    # MH2O table - Liquid data (WotLK+)
    c.execute("""
    CREATE TABLE IF NOT EXISTS mh2o (
        adt_id INTEGER,
        liquid_data BLOB,
        FOREIGN KEY(adt_id) REFERENCES adt_files(id)
    )
    """)
    
    # MCDD table - Detail doodad settings (Cata+)
    c.execute("""
    CREATE TABLE IF NOT EXISTS mcdd (
        mcnk_id INTEGER,
        disable_data BLOB,
        FOREIGN KEY(mcnk_id) REFERENCES mcnk(id)
    )
    """)
    
    # MFBO table - Flying bounding box
    c.execute("""
    CREATE TABLE IF NOT EXISTS mfbo (
        adt_id INTEGER,
        maximum_plane BLOB,
        minimum_plane BLOB,
        FOREIGN KEY(adt_id) REFERENCES adt_files(id)
    )
    """)
    
    # Note: We've removed the 'chunks' table to reduce database size
    
    conn.commit()
    return conn

def insert_adt_record(conn, name, folder_name, x, y, version=0):
    """Insert a record into the adt_files table"""
    c = conn.cursor()
    c.execute("INSERT INTO adt_files (name, folder_name, x_coord, y_coord, version) VALUES (?,?,?,?,?)",
              (name, folder_name, x, y, version))
    return c.lastrowid

def insert_texture(conn, adt_id, texture, file_data_id=None, texture_type=None):
    """Insert a texture record"""
    c = conn.cursor()
    c.execute("INSERT INTO textures (adt_id, texture, file_data_id, texture_type) VALUES (?,?,?,?)", 
              (adt_id, texture, file_data_id, texture_type))

def insert_m2_model(conn, adt_id, model_name):
    """Insert an M2 model record"""
    c = conn.cursor()
    c.execute("INSERT INTO m2_models (adt_id, model_name) VALUES (?,?)",
              (adt_id, model_name))

def insert_wmo_model(conn, adt_id, wmo_name):
    """Insert a WMO model record"""
    c = conn.cursor()
    c.execute("INSERT INTO wmo_models (adt_id, wmo_name) VALUES (?,?)",
              (adt_id, wmo_name))

def insert_mddf(conn, adt_id, uniqueId, model_name, position, rotation, scale, flags, file_data_id=None):
    """Insert an MDDF record (M2 placement)"""
    c = conn.cursor()
    c.execute("""
    INSERT INTO mddf (adt_id, uniqueId, model_name, file_data_id, posX, posY, posZ, rotX, rotY, rotZ, scale, flags)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        adt_id, uniqueId, model_name, file_data_id,
        position[0], position[1], position[2],
        rotation[0], rotation[1], rotation[2],
        scale, flags
    ))
    return c.lastrowid

def insert_modf(conn, adt_id, uniqueId, wmo_name, position, rotation, scale, flags, doodadSet=0, nameSet=0, file_data_id=None):
    """Insert a MODF record (WMO placement)"""
    c = conn.cursor()
    c.execute("""
    INSERT INTO modf (adt_id, uniqueId, wmo_name, file_data_id, posX, posY, posZ, rotX, rotY, rotZ, scale, flags, doodadSet, nameSet)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        adt_id, uniqueId, wmo_name, file_data_id,
        position[0], position[1], position[2],
        rotation[0], rotation[1], rotation[2],
        scale, flags, doodadSet, nameSet
    ))
    return c.lastrowid

def insert_mcnk_data(conn, adt_id, index_x, index_y, flags, areaid, position, has_mcvt=0, has_mcnr=0, has_mclq=0, has_mcsh=0, has_mccv=0, has_mclv=0):
    """Insert an MCNK record (terrain chunk)"""
    c = conn.cursor()
    c.execute("""
    INSERT INTO mcnk (adt_id, index_x, index_y, flags, areaid, position_x, position_y, position_z, 
                     has_mcvt, has_mcnr, has_mclq, has_mcsh, has_mccv, has_mclv)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        adt_id, index_x, index_y, flags, areaid, 
        position[0], position[1], position[2],
        has_mcvt, has_mcnr, has_mclq, has_mcsh, has_mccv, has_mclv
    ))
    return c.lastrowid

def insert_mcvt_data(conn, mcnk_id, heights):
    """Insert an MCVT record (height data)"""
    if heights:
        c = conn.cursor()
        heights_blob = struct.pack('<' + 'f' * len(heights), *heights)
        c.execute("INSERT INTO mcvt (mcnk_id, heights) VALUES (?,?)", (mcnk_id, heights_blob))

def insert_mcnr_data(conn, mcnk_id, normals):
    """Insert an MCNR record (normal data)"""
    if normals:
        c = conn.cursor()
        # Convert normals to a flat list and then to a blob
        flat_normals = []
        for nx, ny, nz in normals:
            flat_normals.extend([nx, ny, nz])
        normals_blob = struct.pack('<' + 'f' * len(flat_normals), *flat_normals)
        c.execute("INSERT INTO mcnr (mcnk_id, normals) VALUES (?,?)", (mcnk_id, normals_blob))

def insert_mcly_data(conn, mcnk_id, layer):
    """Insert an MCLY record (layer data)"""
    if layer:
        c = conn.cursor()
        c.execute("""
        INSERT INTO mcly (mcnk_id, textureId, flags, offsetInMCAL, effectId)
        VALUES (?,?,?,?,?)
        """, (
            mcnk_id, layer['textureId'], layer['flags'], 
            layer['offsetInMCAL'], layer['effectId']
        ))

def insert_mcal_data(conn, mcnk_id, alpha_map, compressed=0):
    """Insert an MCAL record (alpha map data)"""
    if alpha_map:
        c = conn.cursor()
        c.execute("INSERT INTO mcal (mcnk_id, alpha_map, compressed) VALUES (?,?,?)", 
                 (mcnk_id, alpha_map, compressed))

def insert_mcsh_data(conn, mcnk_id, shadow_map):
    """Insert an MCSH record (shadow map data)"""
    if shadow_map:
        c = conn.cursor()
        c.execute("INSERT INTO mcsh (mcnk_id, shadow_map) VALUES (?,?)", (mcnk_id, shadow_map))

def insert_mclq_data(conn, mcnk_id, liquid_data):
    """Insert an MCLQ record (liquid data)"""
    if liquid_data:
        c = conn.cursor()
        c.execute("INSERT INTO mclq (mcnk_id, liquid_data) VALUES (?,?)", (mcnk_id, liquid_data))

def insert_mccv_data(conn, mcnk_id, vertex_colors):
    """Insert an MCCV record (vertex color data)"""
    if vertex_colors:
        c = conn.cursor()
        # Convert vertex colors to a blob
        flat_colors = []
        for r, g, b, a in vertex_colors:
            flat_colors.extend([r, g, b, a])
        colors_blob = struct.pack('<' + 'B' * len(flat_colors), *flat_colors)
        c.execute("INSERT INTO mccv (mcnk_id, vertex_colors) VALUES (?,?)", (mcnk_id, colors_blob))

def insert_mclv_data(conn, mcnk_id, vertex_lighting):
    """Insert an MCLV record (vertex lighting)"""
    if vertex_lighting:
        c = conn.cursor()
        # Convert vertex lighting to a blob
        flat_colors = []
        for r, g, b, a in vertex_lighting:
            flat_colors.extend([r, g, b, a])
        lighting_blob = struct.pack('<' + 'B' * len(flat_colors), *flat_colors)
        c.execute("INSERT INTO mclv (mcnk_id, lighting_data) VALUES (?,?)", (mcnk_id, lighting_blob))

def insert_mcdd_data(conn, mcnk_id, disable_data):
    """Insert a MCDD record (detail doodad settings)"""
    if disable_data:
        c = conn.cursor()
        c.execute("INSERT INTO mcdd (mcnk_id, disable_data) VALUES (?,?)", (mcnk_id, disable_data))

def insert_mamp_data(conn, adt_id, value):
    """Insert a MAMP record (alpha map parameters)"""
    c = conn.cursor()
    c.execute("INSERT INTO mamp (adt_id, value) VALUES (?,?)", (adt_id, value))

def insert_mtxf_data(conn, adt_id, texture_flags):
    """Insert a MTXF record (texture flags)"""
    c = conn.cursor()
    c.execute("INSERT INTO mtxf (adt_id, texture_flags) VALUES (?,?)", (adt_id, texture_flags))

def insert_mtxp_data(conn, adt_id, texture_params):
    """Insert a MTXP record (texture parameters)"""
    c = conn.cursor()
    c.execute("INSERT INTO mtxp (adt_id, texture_params) VALUES (?,?)", (adt_id, texture_params))

def insert_mh2o_data(conn, adt_id, liquid_data):
    """Insert a MH2O record (liquid data)"""
    c = conn.cursor()
    c.execute("INSERT INTO mh2o (adt_id, liquid_data) VALUES (?,?)", (adt_id, liquid_data))

def insert_mcmt_data(conn, adt_id, material_ids):
    """Insert a MCMT record (material IDs)"""
    c = conn.cursor()
    c.execute("INSERT INTO mcmt (adt_id, material_ids) VALUES (?,?)", (adt_id, material_ids))

def insert_mfbo_data(conn, adt_id, maximum_plane, minimum_plane):
    """Insert a MFBO record (flying bounding box)"""
    c = conn.cursor()
    max_blob = struct.pack('<' + 'h' * len(maximum_plane), *maximum_plane)
    min_blob = struct.pack('<' + 'h' * len(minimum_plane), *minimum_plane)
    c.execute("INSERT INTO mfbo (adt_id, maximum_plane, minimum_plane) VALUES (?,?,?)", 
             (adt_id, max_blob, min_blob))

# Note: We've removed the insert_chunk_data function as we're no longer storing raw chunk data
