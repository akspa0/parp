#!/usr/bin/env python3
import json
import sqlite3
import logging
from pathlib import Path
import argparse
from datetime import datetime

class ADTDatabaseExporter:
    def __init__(self, output_dir="output", db_name=None):
        # Create timestamped output directory
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = Path(output_dir) / self.timestamp
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging
        log_file = self.output_dir / f"adt_export_{self.timestamp}.log"
        self.logger = logging.getLogger("ADTDatabaseExporter")
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)

        # Setup database
        if db_name is None:
            db_name = f"adt_data_{self.timestamp}.db"
        self.db_path = self.output_dir / db_name
        self.conn = None
        self.cursor = None

    def setup_database(self):
        """Create the database schema"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()

            # Create main tables
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS adt_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT UNIQUE,
                    map_name TEXT,
                    x_coord INTEGER,
                    y_coord INTEGER,
                    processed_timestamp TEXT
                )
            ''')

            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    adt_id INTEGER,
                    magic TEXT,
                    size INTEGER,
                    chunk_index INTEGER,
                    raw_data TEXT,
                    decoded_data TEXT,
                    chunk_status TEXT,
                    status_message TEXT,
                    FOREIGN KEY (adt_id) REFERENCES adt_files(id)
                )
            ''')

            # Create indices for better query performance
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_chunks_magic ON chunks(magic)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_chunks_adt_id ON chunks(adt_id)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_chunks_status ON chunks(chunk_status)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_adt_files_map ON adt_files(map_name)')

            self.conn.commit()

        except Exception as e:
            self.logger.error(f"Error setting up database: {e}")
            raise

    def extract_coords_from_filename(self, filename):
        """Extract map name and coordinates from ADT filename"""
        try:
            # Example: mapname_XX_YY.adt
            parts = filename.replace('.adt', '').split('_')
            if len(parts) >= 3:
                return {
                    'map_name': '_'.join(parts[:-2]),  # Handle map names with underscores
                    'x_coord': int(parts[-2]),
                    'y_coord': int(parts[-1])
                }
            return None
        except Exception as e:
            self.logger.error(f"Error parsing filename {filename}: {e}")
            return None

    def process_json_file(self, json_path):
        """Process a single JSON file and insert its data into the database"""
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)

            filename = data.get('filename')
            if not filename:
                self.logger.warning(f"No filename found in {json_path}")
                return

            # Extract coordinates and insert file record
            coords = self.extract_coords_from_filename(filename)
            if coords:
                self.cursor.execute('''
                    INSERT OR REPLACE INTO adt_files 
                    (filename, map_name, x_coord, y_coord, processed_timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    filename, 
                    coords['map_name'], 
                    coords['x_coord'], 
                    coords['y_coord'],
                    self.timestamp
                ))
                
                adt_id = self.cursor.lastrowid

                # Process chunks
                for i, chunk in enumerate(data.get('chunks', [])):
                    magic = chunk.get('magic')
                    size = chunk.get('size')
                    raw_data = chunk.get('data', {}).get('raw_data')
                    decoded_data = chunk.get('data', {}).get('decoded')

                    # Determine chunk status and message
                    chunk_status = 'decoded'
                    status_message = None

                    if isinstance(decoded_data, dict):
                        if 'status' in decoded_data:
                            chunk_status = decoded_data['status']
                            status_message = decoded_data.get('message')
                        elif 'error' in decoded_data:
                            chunk_status = 'error'
                            status_message = decoded_data['error']
                    elif decoded_data is None and raw_data:
                        chunk_status = 'unhandled'
                        status_message = 'No decoder available'
                    elif not raw_data:
                        chunk_status = 'empty'
                        status_message = 'Empty chunk (normal)'

                    # Store the full decoded data as JSON
                    decoded_json = json.dumps(decoded_data) if decoded_data else None

                    # Insert chunk record
                    self.cursor.execute('''
                        INSERT INTO chunks (
                            adt_id, magic, size, chunk_index, 
                            raw_data, decoded_data, 
                            chunk_status, status_message
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        adt_id, magic, size, i,
                        raw_data, decoded_json,
                        chunk_status, status_message
                    ))

                self.conn.commit()
                self.logger.info(f"Successfully processed {filename}")

        except Exception as e:
            self.logger.error(f"Error processing JSON file {json_path}: {e}")
            self.conn.rollback()
            raise

    def process_directory(self, directory_path):
        """Process all JSON files in the specified directory"""
        try:
            directory = Path(directory_path)
            json_files = list(directory.glob("*.json"))
            self.logger.info(f"Found {len(json_files)} JSON files to process")

            for json_path in json_files:
                try:
                    self.logger.info(f"Processing {json_path.name}")
                    self.process_json_file(json_path)
                except Exception as e:
                    self.logger.error(f"Error processing {json_path.name}: {e}")
                    continue

            # Generate summary statistics
            self.generate_summary()

        except Exception as e:
            self.logger.error(f"Error processing directory {directory_path}: {e}")
            raise

    def generate_summary(self):
        """Generate and log summary statistics"""
        try:
            # Count total files
            file_count = self.cursor.execute('SELECT COUNT(*) FROM adt_files').fetchone()[0]
            
            # Count chunks by type and status
            chunk_stats = self.cursor.execute('''
                SELECT 
                    magic,
                    chunk_status,
                    COUNT(*) as count
                FROM chunks 
                GROUP BY magic, chunk_status
                ORDER BY magic, chunk_status
            ''').fetchall()

            # Write summary to log
            self.logger.info("\n=== Processing Summary ===")
            self.logger.info(f"Total ADT files processed: {file_count}")
            self.logger.info("\nChunk Statistics:")
            self.logger.info(f"{'Magic':<10} {'Status':<12} {'Count':<8}")
            self.logger.info("-" * 32)
            
            current_magic = None
            total_by_magic = 0
            
            for magic, status, count in chunk_stats:
                if current_magic != magic:
                    if current_magic is not None:
                        self.logger.info(f"{'':<10} {'TOTAL':<12} {total_by_magic:<8}")
                        self.logger.info("-" * 32)
                    current_magic = magic
                    total_by_magic = 0
                    
                self.logger.info(f"{magic:<10} {status:<12} {count:<8}")
                total_by_magic += count

            # Print final total
            if current_magic is not None:
                self.logger.info(f"{'':<10} {'TOTAL':<12} {total_by_magic:<8}")

            # Print overall statistics
            total_stats = self.cursor.execute('''
                SELECT 
                    chunk_status,
                    COUNT(*) as count,
                    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM chunks), 2) as percentage
                FROM chunks
                GROUP BY chunk_status
                ORDER BY count DESC
            ''').fetchall()

            self.logger.info("\nOverall Statistics:")
            self.logger.info(f"{'Status':<12} {'Count':<8} {'Percentage':<8}")
            self.logger.info("-" * 32)
            for status, count, percentage in total_stats:
                self.logger.info(f"{status:<12} {count:<8} {percentage:>7.2f}%")

        except Exception as e:
            self.logger.error(f"Error generating summary: {e}")

    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()

def main():
    parser = argparse.ArgumentParser(description="Convert ADT JSON files to SQLite database")
    parser.add_argument("input_dir", help="Directory containing JSON files")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    parser.add_argument("--db-name", help="Custom database filename")
    args = parser.parse_args()

    exporter = ADTDatabaseExporter(args.output_dir, args.db_name)
    try:
        exporter.setup_database()
        exporter.process_directory(args.input_dir)
    finally:
        exporter.close()

if __name__ == "__main__":
    main()
