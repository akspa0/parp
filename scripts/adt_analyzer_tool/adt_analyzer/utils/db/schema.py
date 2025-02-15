"""Database schema definitions for ADT analyzer."""

# Core tables
CREATE_ADT_FILES_TABLE = """
CREATE TABLE IF NOT EXISTS adt_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_ERRORS_TABLE = """
CREATE TABLE IF NOT EXISTS errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    adt_file_id INTEGER NOT NULL,
    error_message TEXT NOT NULL,
    FOREIGN KEY (adt_file_id) REFERENCES adt_files(id)
);
"""

# Version info
CREATE_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    adt_file_id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    FOREIGN KEY (adt_file_id) REFERENCES adt_files(id)
);
"""

# Header info
CREATE_HEADERS_TABLE = """
CREATE TABLE IF NOT EXISTS headers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    adt_file_id INTEGER NOT NULL,
    flags INTEGER NOT NULL,
    has_mfbo BOOLEAN NOT NULL,
    has_mh2o BOOLEAN NOT NULL,
    has_mtxf BOOLEAN NOT NULL,
    use_big_alpha BOOLEAN NOT NULL,
    use_big_textures BOOLEAN NOT NULL,
    use_mcsh BOOLEAN NOT NULL,
    FOREIGN KEY (adt_file_id) REFERENCES adt_files(id)
);
"""

CREATE_HEADER_OFFSETS_TABLE = """
CREATE TABLE IF NOT EXISTS header_offsets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    header_id INTEGER NOT NULL,
    mcin INTEGER NOT NULL,
    mtex INTEGER NOT NULL,
    mmdx INTEGER NOT NULL,
    mmid INTEGER NOT NULL,
    mwmo INTEGER NOT NULL,
    mwid INTEGER NOT NULL,
    mddf INTEGER NOT NULL,
    modf INTEGER NOT NULL,
    mfbo INTEGER NOT NULL,
    mh2o INTEGER NOT NULL,
    mtxf INTEGER NOT NULL,
    FOREIGN KEY (header_id) REFERENCES headers(id)
);
"""

# Chunk indices
CREATE_CHUNK_INDICES_TABLE = """
CREATE TABLE IF NOT EXISTS chunk_indices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    adt_file_id INTEGER NOT NULL,
    count INTEGER NOT NULL,
    valid_chunks INTEGER NOT NULL,
    FOREIGN KEY (adt_file_id) REFERENCES adt_files(id)
);
"""

CREATE_CHUNK_INDEX_ENTRIES_TABLE = """
CREATE TABLE IF NOT EXISTS chunk_index_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk_indices_id INTEGER NOT NULL,
    entry_index INTEGER NOT NULL,
    offset INTEGER NOT NULL,
    size INTEGER NOT NULL,
    flags INTEGER NOT NULL,
    async_id INTEGER NOT NULL,
    grid_x INTEGER NOT NULL,
    grid_y INTEGER NOT NULL,
    FOREIGN KEY (chunk_indices_id) REFERENCES chunk_indices(id)
);
"""

# Textures
CREATE_TEXTURES_TABLE = """
CREATE TABLE IF NOT EXISTS textures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    adt_file_id INTEGER NOT NULL,
    count INTEGER NOT NULL,
    FOREIGN KEY (adt_file_id) REFERENCES adt_files(id)
);
"""

CREATE_TEXTURE_ENTRIES_TABLE = """
CREATE TABLE IF NOT EXISTS texture_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    textures_id INTEGER NOT NULL,
    texture_path TEXT NOT NULL,
    FOREIGN KEY (textures_id) REFERENCES textures(id)
);
"""

# Models (M2)
CREATE_M2_MODELS_TABLE = """
CREATE TABLE IF NOT EXISTS m2_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    adt_file_id INTEGER NOT NULL,
    count INTEGER NOT NULL,
    data_size INTEGER NOT NULL,
    FOREIGN KEY (adt_file_id) REFERENCES adt_files(id)
);
"""

CREATE_M2_MODEL_ENTRIES_TABLE = """
CREATE TABLE IF NOT EXISTS m2_model_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    m2_models_id INTEGER NOT NULL,
    model_index INTEGER NOT NULL,
    offset INTEGER NOT NULL,
    name TEXT NOT NULL,
    FOREIGN KEY (m2_models_id) REFERENCES m2_models(id)
);
"""

# WMO Models
CREATE_WMO_MODELS_TABLE = """
CREATE TABLE IF NOT EXISTS wmo_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    adt_file_id INTEGER NOT NULL,
    count INTEGER NOT NULL,
    data_size INTEGER NOT NULL,
    FOREIGN KEY (adt_file_id) REFERENCES adt_files(id)
);
"""

CREATE_WMO_MODEL_ENTRIES_TABLE = """
CREATE TABLE IF NOT EXISTS wmo_model_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wmo_models_id INTEGER NOT NULL,
    model_index INTEGER NOT NULL,
    offset INTEGER NOT NULL,
    name TEXT NOT NULL,
    FOREIGN KEY (wmo_models_id) REFERENCES wmo_models(id)
);
"""

# Model Placements
CREATE_M2_PLACEMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS m2_placements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    adt_file_id INTEGER NOT NULL,
    count INTEGER NOT NULL,
    valid_entries INTEGER NOT NULL,
    FOREIGN KEY (adt_file_id) REFERENCES adt_files(id)
);
"""

CREATE_M2_PLACEMENT_ENTRIES_TABLE = """
CREATE TABLE IF NOT EXISTS m2_placement_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    m2_placements_id INTEGER NOT NULL,
    entry_index INTEGER NOT NULL,
    mmid_entry INTEGER NOT NULL,
    unique_id INTEGER NOT NULL,
    position_x REAL NOT NULL,
    position_y REAL NOT NULL,
    position_z REAL NOT NULL,
    rotation_x REAL NOT NULL,
    rotation_y REAL NOT NULL,
    rotation_z REAL NOT NULL,
    scale REAL NOT NULL,
    flags INTEGER NOT NULL,
    FOREIGN KEY (m2_placements_id) REFERENCES m2_placements(id)
);
"""

CREATE_WMO_PLACEMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS wmo_placements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    adt_file_id INTEGER NOT NULL,
    count INTEGER NOT NULL,
    valid_entries INTEGER NOT NULL,
    FOREIGN KEY (adt_file_id) REFERENCES adt_files(id)
);
"""

CREATE_WMO_PLACEMENT_ENTRIES_TABLE = """
CREATE TABLE IF NOT EXISTS wmo_placement_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wmo_placements_id INTEGER NOT NULL,
    entry_index INTEGER NOT NULL,
    mwid_entry INTEGER NOT NULL,
    unique_id INTEGER NOT NULL,
    position_x REAL NOT NULL,
    position_y REAL NOT NULL,
    position_z REAL NOT NULL,
    rotation_x REAL NOT NULL,
    rotation_y REAL NOT NULL,
    rotation_z REAL NOT NULL,
    bounds_min_x REAL NOT NULL,
    bounds_min_y REAL NOT NULL,
    bounds_min_z REAL NOT NULL,
    bounds_max_x REAL NOT NULL,
    bounds_max_y REAL NOT NULL,
    bounds_max_z REAL NOT NULL,
    flags INTEGER NOT NULL,
    doodad_set INTEGER NOT NULL,
    name_set INTEGER NOT NULL,
    scale REAL NOT NULL,
    FOREIGN KEY (wmo_placements_id) REFERENCES wmo_placements(id)
);
"""

# Terrain Chunks
CREATE_TERRAIN_CHUNKS_TABLE = """
CREATE TABLE IF NOT EXISTS terrain_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    adt_file_id INTEGER NOT NULL,
    grid_x INTEGER NOT NULL,
    grid_y INTEGER NOT NULL,
    area_id INTEGER NOT NULL,
    flags INTEGER NOT NULL,
    holes INTEGER NOT NULL,
    liquid_level REAL NOT NULL,
    FOREIGN KEY (adt_file_id) REFERENCES adt_files(id)
);
"""

CREATE_TERRAIN_HEIGHTS_TABLE = """
CREATE TABLE IF NOT EXISTS terrain_heights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    terrain_chunk_id INTEGER NOT NULL,
    vertex_index INTEGER NOT NULL,
    height REAL NOT NULL,
    FOREIGN KEY (terrain_chunk_id) REFERENCES terrain_chunks(id)
);
"""

CREATE_TERRAIN_NORMALS_TABLE = """
CREATE TABLE IF NOT EXISTS terrain_normals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    terrain_chunk_id INTEGER NOT NULL,
    normal_index INTEGER NOT NULL,
    x REAL NOT NULL,
    y REAL NOT NULL,
    z REAL NOT NULL,
    FOREIGN KEY (terrain_chunk_id) REFERENCES terrain_chunks(id)
);
"""

# All table creation statements in order of dependency
ALL_TABLES = [
    CREATE_ADT_FILES_TABLE,
    CREATE_ERRORS_TABLE,
    CREATE_VERSION_TABLE,
    CREATE_HEADERS_TABLE,
    CREATE_HEADER_OFFSETS_TABLE,
    CREATE_CHUNK_INDICES_TABLE,
    CREATE_CHUNK_INDEX_ENTRIES_TABLE,
    CREATE_TEXTURES_TABLE,
    CREATE_TEXTURE_ENTRIES_TABLE,
    CREATE_M2_MODELS_TABLE,
    CREATE_M2_MODEL_ENTRIES_TABLE,
    CREATE_WMO_MODELS_TABLE,
    CREATE_WMO_MODEL_ENTRIES_TABLE,
    CREATE_M2_PLACEMENTS_TABLE,
    CREATE_M2_PLACEMENT_ENTRIES_TABLE,
    CREATE_WMO_PLACEMENTS_TABLE,
    CREATE_WMO_PLACEMENT_ENTRIES_TABLE,
    CREATE_TERRAIN_CHUNKS_TABLE,
    CREATE_TERRAIN_HEIGHTS_TABLE,
    CREATE_TERRAIN_NORMALS_TABLE,
]