# SQLite Schema Design for WoW Map Data

## Overview
This schema is designed to store World of Warcraft map data in a way that:
- Preserves all relationships between components
- Enables reconstruction of ADT/WDT files
- Supports change tracking
- Facilitates map editing tools

## Tables

### maps
Stores top-level map information from WDT files
```sql
CREATE TABLE maps (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,          -- Map name (e.g., "Kalidar")
    format TEXT NOT NULL,        -- "ALPHA" or "RETAIL"
    version INTEGER NOT NULL,    -- MVER version
    flags INTEGER NOT NULL,      -- MPHD flags
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### map_tiles
Stores the 64x64 grid of map tiles
```sql
CREATE TABLE map_tiles (
    id INTEGER PRIMARY KEY,
    map_id INTEGER NOT NULL,
    x INTEGER NOT NULL,          -- Grid X (0-63)
    y INTEGER NOT NULL,          -- Grid Y (0-63)
    flags INTEGER NOT NULL,      -- Tile flags
    has_data BOOLEAN NOT NULL,   -- Whether ADT exists
    adt_file TEXT,              -- ADT filename if exists
    FOREIGN KEY (map_id) REFERENCES maps(id),
    UNIQUE (map_id, x, y)
);
```

### textures
Stores texture file references
```sql
CREATE TABLE textures (
    id INTEGER PRIMARY KEY,
    map_id INTEGER NOT NULL,
    path TEXT NOT NULL,          -- Texture file path
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (map_id) REFERENCES maps(id),
    UNIQUE (map_id, path)
);
```

### models_m2
Stores M2 model references
```sql
CREATE TABLE models_m2 (
    id INTEGER PRIMARY KEY,
    map_id INTEGER NOT NULL,
    path TEXT NOT NULL,          -- Model file path
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (map_id) REFERENCES maps(id),
    UNIQUE (map_id, path)
);
```

### models_wmo
Stores WMO model references
```sql
CREATE TABLE models_wmo (
    id INTEGER PRIMARY KEY,
    map_id INTEGER NOT NULL,
    path TEXT NOT NULL,          -- Model file path
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (map_id) REFERENCES maps(id),
    UNIQUE (map_id, path)
);
```

### model_placements_m2
Stores M2 model placement data
```sql
CREATE TABLE model_placements_m2 (
    id INTEGER PRIMARY KEY,
    map_id INTEGER NOT NULL,
    model_id INTEGER NOT NULL,   -- Reference to models_m2
    unique_id INTEGER NOT NULL,  -- Original unique ID
    pos_x REAL NOT NULL,
    pos_y REAL NOT NULL,
    pos_z REAL NOT NULL,
    rot_x REAL NOT NULL,
    rot_y REAL NOT NULL,
    rot_z REAL NOT NULL,
    scale REAL NOT NULL,
    flags INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (map_id) REFERENCES maps(id),
    FOREIGN KEY (model_id) REFERENCES models_m2(id),
    UNIQUE (map_id, unique_id)
);
```

### model_placements_wmo
Stores WMO model placement data
```sql
CREATE TABLE model_placements_wmo (
    id INTEGER PRIMARY KEY,
    map_id INTEGER NOT NULL,
    model_id INTEGER NOT NULL,   -- Reference to models_wmo
    unique_id INTEGER NOT NULL,  -- Original unique ID
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
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (map_id) REFERENCES maps(id),
    FOREIGN KEY (model_id) REFERENCES models_wmo(id),
    UNIQUE (map_id, unique_id)
);
```

### terrain_chunks
Stores MCNK chunk data
```sql
CREATE TABLE terrain_chunks (
    id INTEGER PRIMARY KEY,
    map_id INTEGER NOT NULL,
    tile_id INTEGER NOT NULL,    -- Reference to map_tiles
    index_x INTEGER NOT NULL,    -- Chunk X within tile (0-15)
    index_y INTEGER NOT NULL,    -- Chunk Y within tile (0-15)
    flags INTEGER NOT NULL,
    area_id INTEGER,
    holes INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (map_id) REFERENCES maps(id),
    FOREIGN KEY (tile_id) REFERENCES map_tiles(id),
    UNIQUE (tile_id, index_x, index_y)
);
```

### terrain_heights
Stores MCVT height data
```sql
CREATE TABLE terrain_heights (
    id INTEGER PRIMARY KEY,
    chunk_id INTEGER NOT NULL,
    index INTEGER NOT NULL,      -- Vertex index (0-144)
    height REAL NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chunk_id) REFERENCES terrain_chunks(id),
    UNIQUE (chunk_id, index)
);
```

### terrain_normals
Stores MCNR normal data
```sql
CREATE TABLE terrain_normals (
    id INTEGER PRIMARY KEY,
    chunk_id INTEGER NOT NULL,
    index INTEGER NOT NULL,      -- Vertex index (0-144)
    x REAL NOT NULL,
    y REAL NOT NULL,
    z REAL NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chunk_id) REFERENCES terrain_chunks(id),
    UNIQUE (chunk_id, index)
);
```

### terrain_layers
Stores MCLY texture layer data
```sql
CREATE TABLE terrain_layers (
    id INTEGER PRIMARY KEY,
    chunk_id INTEGER NOT NULL,
    texture_id INTEGER NOT NULL, -- Reference to textures
    flags INTEGER NOT NULL,
    effect_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chunk_id) REFERENCES terrain_chunks(id),
    FOREIGN KEY (texture_id) REFERENCES textures(id)
);
```

### terrain_shadows
Stores MCSH shadow data
```sql
CREATE TABLE terrain_shadows (
    id INTEGER PRIMARY KEY,
    chunk_id INTEGER NOT NULL,
    data BLOB NOT NULL,         -- Raw shadow map data
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chunk_id) REFERENCES terrain_chunks(id)
);
```

### terrain_liquid
Stores MCLQ liquid data
```sql
CREATE TABLE terrain_liquid (
    id INTEGER PRIMARY KEY,
    chunk_id INTEGER NOT NULL,
    type INTEGER NOT NULL,
    min_height REAL,
    max_height REAL,
    data BLOB,                  -- Raw liquid height data
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chunk_id) REFERENCES terrain_chunks(id)
);
```

### change_history
Tracks changes for versioning
```sql
CREATE TABLE change_history (
    id INTEGER PRIMARY KEY,
    table_name TEXT NOT NULL,
    record_id INTEGER NOT NULL,
    action TEXT NOT NULL,       -- "INSERT", "UPDATE", "DELETE"
    old_values TEXT,           -- JSON of old values
    new_values TEXT,           -- JSON of new values
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT              -- Optional: for multi-user editing
);
```

## Triggers

### Update Timestamps
```sql
-- Example for model_placements_m2
CREATE TRIGGER update_model_placements_m2_timestamp
AFTER UPDATE ON model_placements_m2
BEGIN
    UPDATE model_placements_m2 
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;
```

### Track Changes
```sql
-- Example for model_placements_m2
CREATE TRIGGER track_model_placements_m2_changes
AFTER UPDATE ON model_placements_m2
BEGIN
    INSERT INTO change_history (
        table_name,
        record_id,
        action,
        old_values,
        new_values
    ) VALUES (
        'model_placements_m2',
        NEW.id,
        'UPDATE',
        json_object(
            'pos_x', OLD.pos_x,
            'pos_y', OLD.pos_y,
            'pos_z', OLD.pos_z,
            -- etc.
        ),
        json_object(
            'pos_x', NEW.pos_x,
            'pos_y', NEW.pos_y,
            'pos_z', NEW.pos_z,
            -- etc.
        )
    );
END;
```

## Indexes
```sql
-- Example indexes for common queries
CREATE INDEX idx_map_tiles_coords ON map_tiles(map_id, x, y);
CREATE INDEX idx_terrain_chunks_location ON terrain_chunks(tile_id, index_x, index_y);
CREATE INDEX idx_model_placements_m2_map ON model_placements_m2(map_id);
CREATE INDEX idx_model_placements_wmo_map ON model_placements_wmo(map_id);
CREATE INDEX idx_change_history_record ON change_history(table_name, record_id);
```

## Views

### active_tiles
```sql
CREATE VIEW active_tiles AS
SELECT 
    mt.*,
    m.name as map_name,
    m.format as map_format
FROM map_tiles mt
JOIN maps m ON mt.map_id = m.id
WHERE mt.has_data = 1;
```

### model_placements
```sql
CREATE VIEW model_placements AS
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
JOIN models_wmo wmo ON mp.model_id = wmo.id;
```

## Notes

### Change Tracking
- Each table has created_at/updated_at timestamps
- change_history table tracks all modifications
- Enables undo/redo functionality
- Supports collaborative editing

### Data Integrity
- Foreign key constraints ensure referential integrity
- Unique constraints prevent duplicates
- Triggers maintain timestamps and history
- Views simplify common queries

### Performance
- Indexes on frequently queried columns
- Normalized structure reduces redundancy
- Views for common data access patterns

### Future Considerations
- Add user management for collaborative editing
- Add tags/metadata for organization
- Add export formats (obj, fbx, etc.)
- Add validation rules
- Add backup/restore functionality