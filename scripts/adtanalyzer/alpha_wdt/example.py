"""
Example usage of the WDT/ADT parser.
"""
import sys
import logging
from pathlib import Path
from datetime import datetime

from wdt_adt_parser.format_detector import detect_format
from wdt_adt_parser.formats.alpha.wdt_parser import AlphaWDTParser
from wdt_adt_parser.formats.retail.wdt_parser import RetailWDTParser
from wdt_adt_parser.database import DatabaseManager

def main():
    """Main entry point"""
    if len(sys.argv) < 3:
        print("Usage: python example.py <wdt_file> <db_name>")
        print("Example: python example.py World/Maps/Azeroth/Azeroth.wdt my_analysis")
        sys.exit(1)
    
    # Setup logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'parser_{timestamp}.log')
        ]
    )
    
    wdt_path = sys.argv[1]
    db_name = sys.argv[2]
    
    # Create database path
    if not db_name.endswith('.db'):
        db_name += '.db'
    
    try:
        # Initialize database
        db = DatabaseManager(db_name)
        logging.info(f"Database initialized: {db_name}")
        
        # Detect format and create appropriate parser
        logging.info(f"Parsing WDT file: {wdt_path}")
        format_type = detect_format(Path(wdt_path))
        parser = AlphaWDTParser() if format_type == 'alpha' else RetailWDTParser()
        
        # Parse WDT file
        parser.open(wdt_path)
        try:
            result = parser.parse()
        finally:
            parser.close()
        
        # Insert WDT record
        wdt_id = db.insert_wdt_record(
            path=wdt_path,
            map_name=Path(wdt_path).stem,
            version=parser.version,
            flags=parser.flags or 0,
            wmo_only=result.get('wmo_only', False),
            chunk_order=','.join(parser.chunk_order),
            format=format_type
        )
        
        # Set database connection for parser
        parser.set_database(db, wdt_id)
        
        # Print summary
        print("\nAnalysis Summary:")
        print("-" * 50)
        print(f"WDT File: {wdt_path}")
        print(f"Format: {format_type.upper()}")
        print(f"Version: {parser.version}")
        print(f"Map Name: {Path(wdt_path).stem}")
        print(f"Total Tiles: {len(parser.tiles)}")
        print(f"Active Tiles: {parser.active_tiles}")
        print()
        
        print(f"Results stored in: {db_name}")
        print(f"Log file: parser_{timestamp}.log")
        
        # Print database query examples
        print("\nDatabase Query Examples:")
        print("-" * 50)
        
        # Example queries
        with db.conn as conn:
            # Get latest WDT file info
            wdt = conn.execute("""
                SELECT path, map_name, version, format, analyzed_at
                FROM wdt_files
                ORDER BY id DESC LIMIT 1
            """).fetchone()
            
            if wdt:
                print("\nLatest WDT File:")
                print(f"Path: {wdt['path']}")
                print(f"Map: {wdt['map_name']}")
                print(f"Version: {wdt['version']}")
                print(f"Format: {wdt['format']}")
                print(f"Analyzed: {wdt['analyzed_at']}")
                print()
            
            # Get active tile count
            tiles = conn.execute("""
                SELECT COUNT(*) as count
                FROM map_tiles
                WHERE wdt_id = (SELECT MAX(id) FROM wdt_files)
            """).fetchone()
            print(f"Active Tiles: {tiles['count'] if tiles else 0}")
            
            # Get model statistics
            m2_models = conn.execute("""
                SELECT COUNT(*) as count
                FROM m2_models
                WHERE wdt_id = (SELECT MAX(id) FROM wdt_files)
            """).fetchone()
            
            wmo_models = conn.execute("""
                SELECT COUNT(*) as count
                FROM wmo_models
                WHERE wdt_id = (SELECT MAX(id) FROM wdt_files)
            """).fetchone()
            
            print("\nModel Statistics:")
            print(f"M2 Models: {m2_models['count'] if m2_models else 0}")
            print(f"WMO Models: {wmo_models['count'] if wmo_models else 0}")
        
    except Exception as e:
        logging.error(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()