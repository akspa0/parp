"""
Main entry point for ADT analysis tool.
Handles command line arguments and coordinates parsing process.
"""
import argparse
import sys
import os
from pathlib import Path
import sqlite3
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime

from .parsers.adt_parser import ADTParser
from .models.chunks import ADTFile, ModelPlacement, WMOPlacement
from .utils.binary import normalize_model_path
from .utils.logging import LogManager

class ADTAnalyzer:
    """Main ADT analysis coordinator"""
    
    def __init__(self, log_manager: LogManager):
        """
        Initialize analyzer
        
        Args:
            log_manager: Configured logging manager
        """
        self.logger = log_manager.get_logger('main')
        self.missing_logger = log_manager.get_logger('missing')
        self.log_manager = log_manager
        self.known_files: Set[str] = set()
        
    def setup_database(self, db_path: Path) -> sqlite3.Connection:
        """
        Set up SQLite database for results
        
        Args:
            db_path: Path to database file
            
        Returns:
            Database connection
        """
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Create tables if they don't exist
        c.executescript("""
            CREATE TABLE IF NOT EXISTS adt_files (
                id INTEGER PRIMARY KEY,
                filename TEXT NOT NULL,
                map_name TEXT NOT NULL,
                coord_x INTEGER NOT NULL,
                coord_y INTEGER NOT NULL,
                version INTEGER NOT NULL,
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
            
            CREATE INDEX IF NOT EXISTS idx_adt_coords ON adt_files(map_name, coord_x, coord_y);
            CREATE INDEX IF NOT EXISTS idx_model_placements ON model_placements(adt_id, model_type);
        """)
        
        conn.commit()
        return conn
        
    def load_listfile(self, listfile_path: Path):
        """
        Load known file list
        
        Args:
            listfile_path: Path to listfile
        """
        if not listfile_path.exists():
            self.logger.warning(f"Listfile not found: {listfile_path}")
            return
            
        with open(listfile_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or ';' not in line:
                    continue
                    
                _, filename = line.split(';', 1)
                normalized = normalize_model_path(filename)
                if normalized:
                    self.known_files.add(normalized)
                    
        self.logger.info(f"Loaded {len(self.known_files)} known files")
        
    def check_missing_file(self, filename: str, referenced_by: str):
        """
        Check if file exists in listfile
        
        Args:
            filename: File to check
            referenced_by: Name of referencing file
        """
        if not filename or filename == "<invalid offset>":
            return
            
        normalized = normalize_model_path(filename)
        if normalized and normalized not in self.known_files:
            self.missing_logger.info(f"Missing file: {filename} referenced by {referenced_by}")
            
    def store_adt_data(self, conn: sqlite3.Connection, adt_file: ADTFile, filename: str, map_name: str, coord_x: int, coord_y: int) -> int:
        """
        Store ADT data in database
        
        Args:
            conn: Database connection
            adt_file: Parsed ADT data
            filename: ADT filename
            map_name: Map name
            coord_x: X coordinate
            coord_y: Y coordinate
            
        Returns:
            ADT record ID
        """
        c = conn.cursor()
        
        # Insert ADT file record
        c.execute("""
            INSERT INTO adt_files (filename, map_name, coord_x, coord_y, version)
            VALUES (?, ?, ?, ?, ?)
        """, (filename, map_name, coord_x, coord_y, adt_file.version))
        adt_id = c.lastrowid
        
        # Store textures
        for tex in adt_file.textures:
            c.execute("INSERT INTO textures (adt_id, filename) VALUES (?, ?)",
                     (adt_id, tex.filename))
            self.check_missing_file(tex.filename, filename)
            
        # Store M2 models
        for model in adt_file.m2_models:
            c.execute("INSERT INTO m2_models (adt_id, filename) VALUES (?, ?)",
                     (adt_id, model))
            self.check_missing_file(model, filename)
            
        # Store WMO models
        for model in adt_file.wmo_models:
            c.execute("INSERT INTO wmo_models (adt_id, filename) VALUES (?, ?)",
                     (adt_id, model))
            self.check_missing_file(model, filename)
            
        # Store model placements
        for placement in adt_file.m2_placements:
            model_name = adt_file.m2_models[placement.name_id] if 0 <= placement.name_id < len(adt_file.m2_models) else ""
            c.execute("""
                INSERT INTO model_placements 
                (adt_id, model_type, model_name, unique_id, pos_x, pos_y, pos_z, 
                 rot_x, rot_y, rot_z, scale, flags)
                VALUES (?, 'M2', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (adt_id, model_name, placement.unique_id,
                 placement.position[0], placement.position[1], placement.position[2],
                 placement.rotation[0], placement.rotation[1], placement.rotation[2],
                 placement.scale, placement.flags))
                 
        for placement in adt_file.wmo_placements:
            model_name = adt_file.wmo_models[placement.name_id] if 0 <= placement.name_id < len(adt_file.wmo_models) else ""
            c.execute("""
                INSERT INTO model_placements 
                (adt_id, model_type, model_name, unique_id, pos_x, pos_y, pos_z,
                 rot_x, rot_y, rot_z, scale, flags)
                VALUES (?, 'WMO', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (adt_id, model_name, placement.unique_id,
                 placement.position[0], placement.position[1], placement.position[2],
                 placement.rotation[0], placement.rotation[1], placement.rotation[2],
                 placement.scale, placement.flags))
                 
        # Store MCNK data
        for coord, mcnk in adt_file.mcnk_chunks.items():
            c.execute("""
                INSERT INTO mcnk_data
                (adt_id, index_x, index_y, flags, area_id, holes, liquid_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (adt_id, mcnk.index_x, mcnk.index_y, mcnk.flags,
                 mcnk.area_id, mcnk.holes, mcnk.liquid_type))
                 
        conn.commit()
        return adt_id
        
    def process_directory(self, directory: Path, db_path: Path):
        """
        Process directory of ADT files
        
        Args:
            directory: Directory containing ADT files
            db_path: Path to output database
        """
        if not directory.exists():
            self.logger.error(f"Directory not found: {directory}")
            return
            
        # Set up database
        conn = self.setup_database(db_path)
        
        # Track unique IDs
        unique_ids = set()
        
        # Process ADT files
        adt_pattern = re.compile(r'^(?:.*?)(\d+)_(\d+)\.adt$', re.IGNORECASE)
        map_name = directory.name.lower()
        
        for file_path in directory.glob('*.adt'):
            match = adt_pattern.match(file_path.name)
            if not match:
                self.logger.warning(f"Skipping {file_path.name}, does not match pattern")
                continue
                
            x, y = map(int, match.groups())
            
            try:
                self.logger.info(f"Processing {file_path.name}")
                parser = ADTParser(str(file_path))
                adt_data = parser.parse()
                
                # Store data
                adt_id = self.store_adt_data(conn, adt_data, file_path.name, map_name, x, y)
                
                # Track unique IDs
                for placement in adt_data.m2_placements + adt_data.wmo_placements:
                    unique_ids.add(placement.unique_id)
                    
            except Exception as e:
                self.logger.error(f"Error processing {file_path.name}", exc_info=e)
                
        # Write max unique ID
        if unique_ids:
            max_uid = max(unique_ids)
            uid_path = directory / 'uid.ini'
            with open(uid_path, 'w') as f:
                f.write(f"max_unique_id={max_uid}\n")
            self.logger.info(f"Maximum unique ID: {max_uid}")
            
        conn.close()
        
def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='ADT file analyzer')
    parser.add_argument('directory', help='Directory containing ADT files')
    parser.add_argument('--listfile', help='Path to listfile for checking references')
    parser.add_argument('--db', help='Output database path', default='analysis.db')
    parser.add_argument('--log-dir', help='Log directory')
    args = parser.parse_args()
    
    # Set up logging
    log_dir = Path(args.log_dir) if args.log_dir else None
    log_manager = LogManager(log_dir)
    logger = log_manager.get_logger('main')
    
    try:
        logger.info("Starting ADT analysis")
        analyzer = ADTAnalyzer(log_manager)
        
        # Load listfile if provided
        if args.listfile:
            analyzer.load_listfile(Path(args.listfile))
            
        # Process directory
        analyzer.process_directory(Path(args.directory), Path(args.db))
        
        logger.info("Analysis complete")
        
    except Exception as e:
        logger.error("Fatal error", exc_info=e)
        sys.exit(1)
        
if __name__ == '__main__':
    main()