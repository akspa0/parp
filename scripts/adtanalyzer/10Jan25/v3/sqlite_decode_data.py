#!/usr/bin/env python3
import json
import sqlite3
import logging
from pathlib import Path
import argparse
from datetime import datetime

class DecodedDataExtractor:
    def __init__(self, input_db_path, output_dir="decoded_databases"):
        self.input_db_path = Path(input_db_path)
        self.map_name = self.input_db_path.parent.name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup output database
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_db_path = self.output_dir / f"{self.map_name}_decoded_{timestamp}.db"
        
        # Setup logging
        self.logger = self._setup_logger()
        
        self.input_conn = None
        self.output_conn = None

    def _setup_logger(self):
        logger = logging.getLogger(f"DecodedDataExtractor_{self.map_name}")
        handler = logging.FileHandler(f"decoded_extraction_{self.map_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        return logger

    def setup_output_database(self):
        """Create the schema for the decoded data database"""
        try:
            # Base tables that track source files and chunks
            self.output_conn.execute('''
                CREATE TABLE IF NOT EXISTS source_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_id INTEGER,
                    filename TEXT,
                    map_name TEXT,
                    x_coord INTEGER,
                    y_coord INTEGER
                )
            ''')

            self.output_conn.execute('''
                CREATE TABLE IF NOT EXISTS chunk_registry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_file_id INTEGER,
                    original_chunk_id INTEGER,
                    magic TEXT,
                    chunk_index INTEGER,
                    FOREIGN KEY (source_file_id) REFERENCES source_files(id)
                )
            ''')

            # Tables for specific chunk types
            self.output_conn.execute('''
                CREATE TABLE IF NOT EXISTS texture_names (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chunk_id INTEGER,
                    texture_index INTEGER,
                    texture_name TEXT,
                    FOREIGN KEY (chunk_id) REFERENCES chunk_registry(id)
                )
            ''')

            self.output_conn.execute('''
                CREATE TABLE IF NOT EXISTS model_names (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chunk_id INTEGER,
                    model_index INTEGER,
                    model_name TEXT,
                    FOREIGN KEY (chunk_id) REFERENCES chunk_registry(id)
                )
            ''')

            self.output_conn.execute('''
                CREATE TABLE IF NOT EXISTS model_placements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chunk_id INTEGER,
                    model_index INTEGER,
                    position_x REAL,
                    position_y REAL,
                    position_z REAL,
                    rotation_x REAL,
                    rotation_y REAL,
                    rotation_z REAL,
                    scale REAL,
                    flags INTEGER,
                    FOREIGN KEY (chunk_id) REFERENCES chunk_registry(id)
                )
            ''')

            # Add more tables as needed...

            self.output_conn.commit()

        except Exception as e:
            self.logger.error(f"Error setting up output database: {e}")
            raise

    def process_chunk_data(self, chunk_reg_id, magic, decoded_data):
        """Process decoded data based on chunk type"""
        try:
            if not isinstance(decoded_data, dict):
                decoded_data = json.loads(decoded_data)

            if magic == 'MTEX':
                self._process_textures(chunk_reg_id, decoded_data)
            elif magic == 'MMDX':
                self._process_models(chunk_reg_id, decoded_data)
            elif magic == 'MDDF':
                self._process_model_placements(chunk_reg_id, decoded_data)
            # Add more handlers as needed...

        except Exception as e:
            self.logger.error(f"Error processing {magic} chunk {chunk_reg_id}: {e}")

    def _process_textures(self, chunk_reg_id, data):
        """Process texture names from MTEX chunk"""
        try:
            textures = data.get('textures', [])
            for idx, texture in enumerate(textures):
                self.output_conn.execute('''
                    INSERT INTO texture_names (chunk_id, texture_index, texture_name)
                    VALUES (?, ?, ?)
                ''', (chunk_reg_id, idx, texture))
        except Exception as e:
            self.logger.error(f"Error processing textures for chunk {chunk_reg_id}: {e}")

    def _process_models(self, chunk_reg_id, data):
        """Process model names from MMDX chunk"""
        try:
            models = data.get('models', [])
            for idx, model in enumerate(models):
                self.output_conn.execute('''
                    INSERT INTO model_names (chunk_id, model_index, model_name)
                    VALUES (?, ?, ?)
                ''', (chunk_reg_id, idx, model))
        except Exception as e:
            self.logger.error(f"Error processing models for chunk {chunk_reg_id}: {e}")

    def _process_model_placements(self, chunk_reg_id, data):
        """Process model placement data from MDDF chunk"""
        try:
            placements = data.get('placements', [])
            for placement in placements:
                self.output_conn.execute('''
                    INSERT INTO model_placements (
                        chunk_id, model_index, 
                        position_x, position_y, position_z,
                        rotation_x, rotation_y, rotation_z,
                        scale, flags
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    chunk_reg_id,
                    placement.get('model_index'),
                    placement.get('position', {}).get('x'),
                    placement.get('position', {}).get('y'),
                    placement.get('position', {}).get('z'),
                    placement.get('rotation', {}).get('x'),
                    placement.get('rotation', {}).get('y'),
                    placement.get('rotation', {}).get('z'),
                    placement.get('scale'),
                    placement.get('flags')
                ))
        except Exception as e:
            self.logger.error(f"Error processing model placements for chunk {chunk_reg_id}: {e}")

def extract_data(self):
    """Main process to extract and transform the data"""
    try:
        self.logger.info(f"Starting extraction from {self.input_db_path}")
        self.input_conn = sqlite3.connect(self.input_db_path)
        self.output_conn = sqlite3.connect(self.output_db_path)

        # Setup output database schema
        self.setup_output_database()

        # Copy and transform file information
        input_cursor = self.input_conn.cursor()
        input_cursor.execute("SELECT id, filename, map_name, x_coord, y_coord FROM adt_files")
        for file_row in input_cursor.fetchall():
            orig_id, filename, map_name, x, y = file_row
            
            cursor = self.output_conn.execute('''
                INSERT INTO source_files (original_id, filename, map_name, x_coord, y_coord)
                VALUES (?, ?, ?, ?, ?)
            ''', (orig_id, filename, map_name, x, y))
            new_file_id = cursor.lastrowid

            # Process chunks for this file
            chunks = input_cursor.execute('''
                SELECT id, magic, chunk_index, decoded_data 
                FROM chunks 
                WHERE adt_id = ? AND chunk_status = 'decoded'
                AND decoded_data IS NOT NULL
            ''', (orig_id,)).fetchall()

            for chunk_row in chunks:
                chunk_id, magic, chunk_index, decoded_data = chunk_row
                
                # Register chunk in new database
                cursor = self.output_conn.execute('''
                    INSERT INTO chunk_registry (
                        source_file_id, original_chunk_id, 
                        magic, chunk_index
                    ) VALUES (?, ?, ?, ?)
                ''', (new_file_id, chunk_id, magic, chunk_index))
                new_chunk_id = cursor.lastrowid

                # Process the decoded data
                if decoded_data:
                    self.process_chunk_data(new_chunk_id, magic, decoded_data)

            self.output_conn.commit()

        self.generate_summary()

    except Exception as e:
        self.logger.error(f"Error during data extraction: {e}")
        raise
    finally:
        if self.input_conn:
            self.input_conn.close()
        if self.output_conn:
            self.output_conn.close()

    def generate_summary(self):
        """Generate summary of extracted data"""
        try:
            self.logger.info("\n=== Extraction Summary ===")
            
            # Count records in each table
            tables = [
                'source_files',
                'chunk_registry',
                'texture_names',
                'model_names',
                'model_placements'
            ]
            
            for table in tables:
                count = self.output_conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                self.logger.info(f"{table}: {count} records")

        except Exception as e:
            self.logger.error(f"Error generating summary: {e}")

def main():
    parser = argparse.ArgumentParser(description="Extract decoded data from ADT database into analyzed format")
    parser.add_argument("input_db", help="Path to input SQLite database")
    parser.add_argument("--output-dir", default="decoded_databases", help="Output directory for decoded databases")
    args = parser.parse_args()

    extractor = DecodedDataExtractor(args.input_db, args.output_dir)
    extractor.extract_data()

if __name__ == "__main__":
    main()
