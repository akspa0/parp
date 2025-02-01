#!/usr/bin/env python3
import argparse
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

class ADTDatabaseExporter:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.output_dir / f"adt_export_{timestamp}.log"
        
        self.logger = logging.getLogger("ADTExporter")
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)

    def create_database(self, map_name: str) -> sqlite3.Connection:
        """Create a new SQLite database with the required schema."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        db_path = self.output_dir / map_name / f"adt_data_{map_name}_{timestamp}.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
        CREATE TABLE adt_files (
            id INTEGER PRIMARY KEY,
            filename TEXT NOT NULL,
            map_name TEXT NOT NULL,
            x_coord INTEGER,
            y_coord INTEGER,
            processed_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        cursor.execute("""
        CREATE TABLE chunks (
            id INTEGER PRIMARY KEY,
            adt_id INTEGER,
            magic TEXT NOT NULL,
            size INTEGER NOT NULL,
            chunk_index INTEGER,
            raw_data TEXT,
            decoded_data TEXT,
            chunk_status TEXT NOT NULL,
            status_message TEXT,
            FOREIGN KEY (adt_id) REFERENCES adt_files(id)
        )
        """)
        
        conn.commit()
        return conn

    def extract_coords(self, filename: str) -> tuple:
        """Extract X,Y coordinates from ADT filename."""
        try:
            # ADT files are typically named map_XX_YY.adt
            parts = filename.split('_')
            if len(parts) >= 3:
                x = int(parts[-2])
                y = int(parts[-1].split('.')[0])
                return x, y
        except:
            pass
        return None, None

    def process_json_file(self, conn: sqlite3.Connection, json_path: Path, map_name: str):
        """Process a single JSON file and insert its data into the database."""
        cursor = conn.cursor()
        
        try:
            with open(json_path) as f:
                data = json.load(f)
            
            # Insert file record
            x_coord, y_coord = self.extract_coords(data['file_info']['name'])
            cursor.execute(
                "INSERT INTO adt_files (filename, map_name, x_coord, y_coord) VALUES (?, ?, ?, ?)",
                (data['file_info']['name'], map_name, x_coord, y_coord)
            )
            adt_id = cursor.lastrowid
            
            # Process regular chunks
            for chunk in data['chunks']:
                self._insert_chunk(cursor, chunk, adt_id)
            
            # Process MCNK chunks
            for chunk in data['mcnk_chunks']:
                self._insert_chunk(cursor, chunk, adt_id, is_mcnk=True)
            
            conn.commit()
            
        except Exception as e:
            self.logger.error(f"Error processing {json_path}: {e}")
            conn.rollback()

    def _insert_chunk(self, cursor: sqlite3.Connection, chunk: Dict[str, Any], adt_id: int, is_mcnk: bool = False):
        """Insert a chunk record into the database."""
        try:
            if 'error' in chunk.get('decoded_data', {}):
                status = 'error'
                status_message = chunk['decoded_data']['error']
            elif chunk.get('decoded_data'):
                status = 'decoded'
                status_message = None
            else:
                status = 'unhandled'
                status_message = chunk.get('data', {}).get('message')

            cursor.execute("""
                INSERT INTO chunks (
                    adt_id, magic, size, chunk_index, raw_data, 
                    decoded_data, chunk_status, status_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                adt_id,
                chunk['magic'],
                chunk['size'],
                chunk.get('index') if is_mcnk else None,
                chunk.get('data', {}).get('raw_data'),
                json.dumps(chunk['decoded_data']) if chunk.get('decoded_data') else None,
                status,
                status_message
            ))
        except Exception as e:
            self.logger.error(f"Error inserting chunk {chunk.get('magic')}: {e}")
            raise

    def process_directory(self, input_dir: str):
        """Process all JSON files in the input directory."""
        input_path = Path(input_dir)
        if not input_path.exists():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")

        # Process each map directory
        for map_dir in input_path.iterdir():
            if not map_dir.is_dir():
                continue

            map_name = map_dir.name
            self.logger.info(f"Processing map: {map_name}")
            
            # Create database for this map
            conn = self.create_database(map_name)
            
            # Process initial analysis files
            initial_dir = map_dir / "initial_analysis"
            if initial_dir.exists():
                for json_file in initial_dir.glob("*.json"):
                    self.logger.info(f"Processing initial analysis: {json_file.name}")
                    self.process_json_file(conn, json_file, map_name)
            
            # Process decoded data files
            decoded_dir = map_dir / "decoded_data"
            if decoded_dir.exists():
                for json_file in decoded_dir.glob("*.json"):
                    self.logger.info(f"Processing decoded data: {json_file.name}")
                    self.process_json_file(conn, json_file, map_name)
            
            conn.close()

def main():
    parser = argparse.ArgumentParser(description="Convert ADT JSON files to SQLite databases")
    parser.add_argument("input_dir", help="Directory containing processed JSON files")
    parser.add_argument("--output-dir", default="databases", help="Directory to save SQLite databases")
    args = parser.parse_args()

    try:
        exporter = ADTDatabaseExporter(args.output_dir)
        exporter.process_directory(args.input_dir)
    except Exception as e:
        logging.error(f"Export failed: {e}")
        raise

if __name__ == "__main__":
    main()
