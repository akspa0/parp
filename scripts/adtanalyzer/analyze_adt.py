#!/usr/bin/env python3
"""
ADT (Area Definition Table) file analyzer.
A standalone script for parsing and analyzing World of Warcraft ADT files.
Based on specifications from: https://wowdev.wiki/ADT/v18
"""
import os
import re
import sys
import struct
import sqlite3
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple, Union
from enum import IntFlag, auto
from pathlib import Path

# Common WoW data types
@dataclass
class Vector3D:
    """3D vector"""
    x: float
    y: float
    z: float
    
    @classmethod
    def unpack(cls, data: bytes, offset: int = 0) -> 'Vector3D':
        """Unpack from binary data"""
        x, y, z = struct.unpack('<3f', data[offset:offset+12])
        return cls(x, y, z)

@dataclass
class Quaternion:
    """Quaternion (x, y, z, w)"""
    x: float
    y: float
    z: float
    w: float
    
    @classmethod
    def from_euler(cls, x: float, y: float, z: float) -> 'Quaternion':
        """Create from Euler angles (radians)"""
        import math
        cx = math.cos(x * 0.5)
        sx = math.sin(x * 0.5)
        cy = math.cos(y * 0.5)
        sy = math.sin(y * 0.5)
        cz = math.cos(z * 0.5)
        sz = math.sin(z * 0.5)
        
        return cls(
            x=sx * cy * cz - cx * sy * sz,
            y=cx * sy * cz + sx * cy * sz,
            z=cx * cy * sz - sx * sy * cz,
            w=cx * cy * cz + sx * sy * sz
        )

@dataclass
class RGBA:
    """RGBA color"""
    r: int
    g: int
    b: int
    a: int

@dataclass
class CAaBox:
    """Axis-aligned bounding box"""
    min: Vector3D
    max: Vector3D

# ADT data structures
class MCNKFlags(IntFlag):
    """Flags used in MCNK chunks"""
    HasMCVT = auto()  # Has vertex height data
    HasMCNR = auto()  # Has normal data
    HasMCLY = auto()  # Has texture layer data
    HasMCRF = auto()  # Has doodad references
    HasMCAL = auto()  # Has alpha maps
    HasMCSH = auto()  # Has shadow map
    HasMCSE = auto()  # Has sound emitters
    HasMCLQ = auto()  # Has liquid data
    HasMCCV = auto()  # Has vertex colors

@dataclass
class TextureInfo:
    """Texture information"""
    filename: str
    flags: int = 0
    effect_id: Optional[int] = None

@dataclass
class ModelPlacement:
    """Base class for model placement data"""
    name_id: int
    unique_id: int
    position: Vector3D
    rotation: Vector3D
    scale: float
    flags: int

@dataclass
class WMOPlacement(ModelPlacement):
    """Additional WMO placement data"""
    doodad_set: int
    name_set: int
    bounding_box: CAaBox

@dataclass
class MCNKInfo:
    """MCNK chunk information"""
    flags: MCNKFlags
    index_x: int
    index_y: int
    n_layers: int
    n_doodad_refs: int
    position: Vector3D
    area_id: int
    holes: int
    layer_flags: int
    render_flags: int
    has_layer_height: bool
    min_elevation: float
    max_elevation: float
    liquid_type: int
    predTex: int
    noEffectDoodad: int
    holes_high_res: int

def try_parse_chunks(data: bytes, reverse_names: bool = False) -> List[Tuple[bytes, bytes]]:
    """Try to parse first few chunks to detect format"""
    pos = 0
    size = len(data)
    chunks = []
    while pos + 8 <= size:
        chunk_name = data[pos:pos+4]
        if reverse_names:
            chunk_name = chunk_name[::-1]
        chunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]
        if pos + 8 + chunk_size > size:
            break
        chunk_data = data[pos+8:pos+8+chunk_size]
        chunks.append((chunk_name, chunk_data))
        pos += 8 + chunk_size
        if len(chunks) > 10:  # Only need first few chunks
            break
    return chunks

def detect_chunk_reversal(data: bytes) -> bool:
    """Detect if chunk names are reversed"""
    normal_chunks = try_parse_chunks(data, False)
    reversed_chunks = try_parse_chunks(data, True)
    
    normal_known = any(c[0] in [b'MVER', b'MHDR', b'MCIN', b'MTEX'] for c in normal_chunks)
    reversed_known = any(c[0] in [b'MVER', b'MHDR', b'MCIN', b'MTEX'] for c in reversed_chunks)
    
    if normal_known and not reversed_known:
        return False
    elif reversed_known and not normal_known:
        return True
    return False

def setup_logging(timestamp: str) -> Tuple[logging.Logger, logging.Logger]:
    """Set up logging"""
    # Main logger
    logger = logging.getLogger('adt_analyzer')
    logger.setLevel(logging.DEBUG)
    
    file_handler = logging.FileHandler(f"adt_parser_{timestamp}.log")
    file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    
    # Missing files logger
    missing_logger = logging.getLogger('missing_files')
    missing_logger.setLevel(logging.INFO)
    missing_handler = logging.FileHandler(f"missing_files_{timestamp}.log")
    missing_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    missing_logger.addHandler(missing_handler)
    
    return logger, missing_logger

def setup_database(db_path: str) -> sqlite3.Connection:
    """Set up SQLite database"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.executescript("""
        CREATE TABLE IF NOT EXISTS adt_files (
            id INTEGER PRIMARY KEY,
            filename TEXT NOT NULL,
            map_name TEXT NOT NULL,
            coord_x INTEGER NOT NULL,
            coord_y INTEGER NOT NULL,
            version INTEGER NOT NULL DEFAULT 18,
            UNIQUE(map_name, coord_x, coord_y)
        );
        
        CREATE TABLE IF NOT EXISTS textures (
            id INTEGER PRIMARY KEY,
            adt_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            FOREIGN KEY(adt_id) REFERENCES adt_files(id)
        );
        
        CREATE TABLE IF NOT EXISTS m2_models (
            id INTEGER PRIMARY KEY,
            adt_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            FOREIGN KEY(adt_id) REFERENCES adt_files(id)
        );
        
        CREATE TABLE IF NOT EXISTS wmo_models (
            id INTEGER PRIMARY KEY,
            adt_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            FOREIGN KEY(adt_id) REFERENCES adt_files(id)
        );
        
        CREATE TABLE IF NOT EXISTS model_placements (
            id INTEGER PRIMARY KEY,
            adt_id INTEGER NOT NULL,
            model_type TEXT NOT NULL,
            model_name TEXT NOT NULL,
            unique_id INTEGER NOT NULL,
            pos_x REAL NOT NULL,
            pos_y REAL NOT NULL,
            pos_z REAL NOT NULL,
            rot_x REAL NOT NULL,
            rot_y REAL NOT NULL,
            rot_z REAL NOT NULL,
            scale REAL NOT NULL,
            flags INTEGER NOT NULL,
            FOREIGN KEY(adt_id) REFERENCES adt_files(id)
        );
        
        CREATE TABLE IF NOT EXISTS mcnk_data (
            id INTEGER PRIMARY KEY,
            adt_id INTEGER NOT NULL,
            index_x INTEGER NOT NULL,
            index_y INTEGER NOT NULL,
            flags INTEGER NOT NULL,
            area_id INTEGER NOT NULL,
            holes INTEGER NOT NULL,
            liquid_type INTEGER NOT NULL,
            FOREIGN KEY(adt_id) REFERENCES adt_files(id)
        );
    """)
    
    conn.commit()
    return conn

def read_cstring(data: bytes, offset: int = 0) -> Tuple[str, int]:
    """Read null-terminated string"""
    end = data.find(b'\0', offset)
    if end == -1:
        return data[offset:].decode('utf-8', errors='replace'), len(data)
    return data[offset:end].decode('utf-8', errors='replace'), end + 1

def normalize_filename(fname: str) -> str:
    """Normalize file path"""
    if not fname or fname == "<invalid offset>":
        return ""
    
    fname = fname.lower().replace('\\', '/')
    fname = fname.lstrip('./').lstrip('/')
    fname = re.sub('/+', '/', fname)
    
    if fname.endswith('.mdx'):
        fname = fname[:-4] + '.m2'
    
    return fname

def parse_adt(file_path: str, logger: logging.Logger) -> Dict:
    """Parse ADT file"""
    with open(file_path, 'rb') as f:
        data = f.read()
    
    # Detect chunk name orientation
    reverse_names = detect_chunk_reversal(data)
    logger.debug(f"Chunk names {'are' if reverse_names else 'are not'} reversed")
    
    pos = 0
    size = len(data)
    
    version = 18  # Default version if MVER not found
    textures = []
    m2_models = []
    wmo_models = []
    m2_placements = []
    wmo_placements = []
    mcnk_chunks = {}
    
    mmdx_block = b''
    mmid_offsets = []
    mwmo_block = b''
    mwid_offsets = []
    
    while pos + 8 <= size:
        # Read chunk header
        chunk_name = data[pos:pos+4]
        if reverse_names:
            chunk_name = chunk_name[::-1]
        
        chunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]
        if pos + 8 + chunk_size > size:
            logger.warning(f"Chunk extends beyond file size at offset {pos}")
            break
            
        chunk_data = data[pos+8:pos+8+chunk_size]
        pos += 8 + chunk_size
        
        logger.debug(f"Found chunk: {chunk_name} Size: {chunk_size}")
        
        try:
            if chunk_name == b'MVER':
                version = struct.unpack('<I', chunk_data[0:4])[0]
                logger.debug(f"ADT version: {version}")
                
            elif chunk_name == b'MTEX':
                # Parse texture names
                offset = 0
                while offset < len(chunk_data):
                    name, offset = read_cstring(chunk_data, offset)
                    if name:
                        textures.append(TextureInfo(name))
                        
            elif chunk_name == b'MMDX':
                mmdx_block = chunk_data
                logger.debug(f"MMDX block length: {len(mmdx_block)}")
                
            elif chunk_name == b'MMID':
                count = len(chunk_data)//4
                mmid_offsets = list(struct.unpack(f'<{count}I', chunk_data))
                logger.debug(f"Found {len(mmid_offsets)} MMID offsets")
                
            elif chunk_name == b'MWMO':
                mwmo_block = chunk_data
                logger.debug(f"MWMO block length: {len(mwmo_block)}")
                
            elif chunk_name == b'MWID':
                count = len(chunk_data)//4
                mwid_offsets = list(struct.unpack(f'<{count}I', chunk_data))
                logger.debug(f"Found {len(mwid_offsets)} MWID offsets")
                
            elif chunk_name == b'MDDF':
                entry_size = 36
                for i in range(0, len(chunk_data), entry_size):
                    entry = chunk_data[i:i+entry_size]
                    if len(entry) == entry_size:
                        name_id, unique_id = struct.unpack('<2I', entry[0:8])
                        position = Vector3D.unpack(entry[8:20])
                        rotation = Vector3D.unpack(entry[20:32])
                        scale = struct.unpack('<f', entry[32:36])[0]
                        flags = struct.unpack('<I', entry[36:40])[0]
                        
                        m2_placements.append(ModelPlacement(
                            name_id=name_id,
                            unique_id=unique_id,
                            position=position,
                            rotation=rotation,
                            scale=scale/1024.0,
                            flags=flags
                        ))
                        
            elif chunk_name == b'MODF':
                entry_size = 64
                for i in range(0, len(chunk_data), entry_size):
                    entry = chunk_data[i:i+entry_size]
                    if len(entry) == entry_size:
                        name_id, unique_id = struct.unpack('<2I', entry[0:8])
                        position = Vector3D.unpack(entry[8:20])
                        rotation = Vector3D.unpack(entry[20:32])
                        
                        bounding_box = CAaBox(
                            Vector3D.unpack(entry[32:44]),
                            Vector3D.unpack(entry[44:56])
                        )
                        
                        flags, doodad_set, name_set, scale = struct.unpack('<4H', entry[56:64])
                        
                        wmo_placements.append(WMOPlacement(
                            name_id=name_id,
                            unique_id=unique_id,
                            position=position,
                            rotation=rotation,
                            scale=scale/1024.0,
                            flags=flags,
                            doodad_set=doodad_set,
                            name_set=name_set,
                            bounding_box=bounding_box
                        ))
                        
            elif chunk_name == b'MCNK':
                if len(chunk_data) >= 128:
                    flags = MCNKFlags(struct.unpack('<I', chunk_data[0:4])[0])
                    ix, iy = struct.unpack('<2I', chunk_data[4:12])
                    n_layers, n_refs = struct.unpack('<2I', chunk_data[12:20])
                    position = Vector3D.unpack(chunk_data[20:32])
                    area_id, holes = struct.unpack('<2I', chunk_data[32:40])
                    layer_flags, render_flags = struct.unpack('<2I', chunk_data[40:48])
                    
                    has_height = bool(chunk_data[48])
                    min_elev, max_elev = struct.unpack('<2f', chunk_data[49:57])
                    liquid_type = struct.unpack('<I', chunk_data[57:61])[0]
                    pred_tex, noeff_doodad, holes_high = struct.unpack('<3H', chunk_data[61:67])
                    
                    mcnk_chunks[(ix, iy)] = MCNKInfo(
                        flags=flags,
                        index_x=ix,
                        index_y=iy,
                        n_layers=n_layers,
                        n_doodad_refs=n_refs,
                        position=position,
                        area_id=area_id,
                        holes=holes,
                        layer_flags=layer_flags,
                        render_flags=render_flags,
                        has_layer_height=has_height,
                        min_elevation=min_elev,
                        max_elevation=max_elev,
                        liquid_type=liquid_type,
                        predTex=pred_tex,
                        noEffectDoodad=noeff_doodad,
                        holes_high_res=holes_high
                    )
                    
        except Exception as e:
            logger.warning(f"Error parsing chunk {chunk_name}: {e}")
    
    # Process model names
    if mmdx_block and mmid_offsets:
        offset = 0
        while offset < len(mmdx_block):
            name, offset = read_cstring(mmdx_block, offset)
            if name:
                m2_models.append(name)
    
    if mwmo_block and mwid_offsets:
        offset = 0
        while offset < len(mwmo_block):
            name, offset = read_cstring(mwmo_block, offset)
            if name:
                wmo_models.append(name)
    
    return {
        'version': version,
        'textures': textures,
        'm2_models': m2_models,
        'wmo_models': wmo_models,
        'm2_placements': m2_placements,
        'wmo_placements': wmo_placements,
        'mcnk_chunks': mcnk_chunks
    }

def process_directory(directory: str, listfile_path: str, db_path: str):
    """Process directory of ADT files"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger, missing_logger = setup_logging(timestamp)
    
    logger.info(f"Starting analysis of ADT files in {directory}")
    conn = setup_database(db_path)
    
    # Load known files
    known_files = set()
    if os.path.exists(listfile_path):
        with open(listfile_path, 'r', encoding='utf-8') as f:
            for line in f:
                if ';' in line:
                    _, filename = line.strip().split(';', 1)
                    norm = normalize_filename(filename)
                    if norm:
                        known_files.add(norm)
        logger.info(f"Loaded {len(known_files)} known files")
    
    # Track unique IDs
    unique_ids = set()
    
    # Process ADT files
    map_name = os.path.basename(directory).lower()
    pattern = re.compile(r'^(?:.*?)(\d+)_(\d+)\.adt$', re.IGNORECASE)
    
    for filename in os.listdir(directory):
        if not filename.lower().endswith('.adt'):
            continue
            
        match = pattern.search(filename)
        if not match:
            logger.warning(f"Skipping {filename}, does not match pattern")
            continue
            
        x, y = map(int, match.groups())
        filepath = os.path.join(directory, filename)
        
        try:
            logger.info(f"Processing {filename}")
            adt_data = parse_adt(filepath, logger)
            
            # Store in database
            c = conn.cursor()
            
            # Insert ADT record
            c.execute("""
                INSERT INTO adt_files (filename, map_name, coord_x, coord_y, version)
                VALUES (?, ?, ?, ?, ?)
            """, (filename, map_name, x, y, adt_data['version']))
            adt_id = c.lastrowid
            
            # Store textures
            for tex in adt_data['textures']:
                c.execute("INSERT INTO textures (adt_id, filename) VALUES (?, ?)",
                         (adt_id, tex.filename))
                if tex.filename:
                    norm = normalize_filename(tex.filename)
                    if norm and norm not in known_files:
                        missing_logger.info(f"Missing texture: {tex.filename} in {filename}")
            
            # Store models
            for model in adt_data['m2_models']:
                c.execute("INSERT INTO m2_models (adt_id, filename) VALUES (?, ?)",
                         (adt_id, model))
                if model:
                    norm = normalize_filename(model)
                    if norm and norm not in known_files:
                        missing_logger.info(f"Missing M2: {model} in {filename}")
            
            for model in adt_data['wmo_models']:
                c.execute("INSERT INTO wmo_models (adt_id, filename) VALUES (?, ?)",
                         (adt_id, model))
                if model:
                    norm = normalize_filename(model)
                    if norm and norm not in known_files:
                        missing_logger.info(f"Missing WMO: {model} in {filename}")
            
            # Store placements
            for m2 in adt_data['m2_placements']:
                model_name = adt_data['m2_models'][m2.name_id] if 0 <= m2.name_id < len(adt_data['m2_models']) else ""
                c.execute("""
                    INSERT INTO model_placements
                    (adt_id, model_type, model_name, unique_id,
                     pos_x, pos_y, pos_z, rot_x, rot_y, rot_z,
                     scale, flags)
                    VALUES (?, 'M2', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (adt_id, model_name, m2.unique_id,
                     m2.position.x, m2.position.y, m2.position.z,
                     m2.rotation.x, m2.rotation.y, m2.rotation.z,
                     m2.scale, m2.flags))
                unique_ids.add(m2.unique_id)
            
            for wmo in adt_data['wmo_placements']:
                model_name = adt_data['wmo_models'][wmo.name_id] if 0 <= wmo.name_id < len(adt_data['wmo_models']) else ""
                c.execute("""
                    INSERT INTO model_placements
                    (adt_id, model_type, model_name, unique_id,
                     pos_x, pos_y, pos_z, rot_x, rot_y, rot_z,
                     scale, flags)
                    VALUES (?, 'WMO', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (adt_id, model_name, wmo.unique_id,
                     wmo.position.x, wmo.position.y, wmo.position.z,
                     wmo.rotation.x, wmo.rotation.y, wmo.rotation.z,
                     wmo.scale, wmo.flags))
                unique_ids.add(wmo.unique_id)
            
            # Store MCNK data
            for coord, mcnk in adt_data['mcnk_chunks'].items():
                c.execute("""
                    INSERT INTO mcnk_data
                    (adt_id, index_x, index_y, flags, area_id,
                     holes, liquid_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (adt_id, mcnk.index_x, mcnk.index_y,
                     mcnk.flags.value, mcnk.area_id,
                     mcnk.holes, mcnk.liquid_type))
            
            conn.commit()
            logger.info(f"Processed {filename}")
            
        except Exception as e:
            logger.error(f"Error processing {filename}: {e}", exc_info=True)
            conn.rollback()
    
    # Write max unique ID
    if unique_ids:
        max_uid = max(unique_ids)
        with open(os.path.join(directory, 'uid.ini'), 'w') as f:
            f.write(f"max_unique_id={max_uid}\n")
        logger.info(f"Maximum unique ID: {max_uid}")
    
    conn.close()
    logger.info("Analysis complete")

def main():
    """Main entry point"""
    if len(sys.argv) < 3:
        print("Usage: python analyze_adt.py <directory_of_adts> <listfile_path> [database_path]")
        sys.exit(1)
    
    directory = sys.argv[1]
    listfile_path = sys.argv[2]
    db_path = sys.argv[3] if len(sys.argv) > 3 else "analysis.db"
    
    process_directory(directory, listfile_path, db_path)

if __name__ == '__main__':
    main()