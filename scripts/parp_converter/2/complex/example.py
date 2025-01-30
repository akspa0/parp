"""
Example usage of the WDT/ADT parser with database functionality.
"""
import sys
import logging
from pathlib import Path
from datetime import datetime

from wdt_adt_parser.universal_parser import create_parser
from wdt_adt_parser.database import DatabaseManager

def setup_logging():
    """Setup logging configuration"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"parser_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return log_filename

def analyze_map(wdt_path: str, db_path: str = None, adt_dir: str = None):
    """
    Analyze a WoW map file (WDT + ADTs) and store results in database
    
    Args:
        wdt_path: Path to WDT file
        db_path: Optional path to SQLite database (default: map_name.db)
        adt_dir: Optional directory containing ADT files
    """
    wdt_path = Path(wdt_path)
    if not wdt_path.exists():
        print(f"Error: WDT file not found: {wdt_path}")
        return
    
    # Setup logging
    log_file = setup_logging()
    logger = logging.getLogger(__name__)
    logger.info(f"Starting analysis of {wdt_path}")
    
    try:
        # Create database path if not provided
        if not db_path:
            db_path = wdt_path.with_suffix('.db')
        
        # Create parser
        parser = create_parser()
        
        # Parse map with database storage
        result = parser.parse_map(
            wdt_path=wdt_path,
            adt_dir=adt_dir,
            db_path=db_path
        )
        
        # Print summary
        print("\nAnalysis Summary:")
        print("-" * 50)
        print(f"WDT File: {wdt_path}")
        print(f"Format: {result['format'].upper()}")
        if 'version' in result:
            print(f"Version: {result['version']}")
        
        # Print tile statistics
        if 'tiles' in result:
            total_tiles = len(result['tiles'])
            active_tiles = len([t for t in result['tiles'] 
                              if t.get('flags_decoded', {}).get('has_adt')])
            print(f"\nTile Statistics:")
            print(f"Total Tiles: {total_tiles}")
            print(f"Active Tiles: {active_tiles}")
            
            # Print ADT statistics if available
            if 'adt_data' in result:
                adt_count = len(result['adt_data'])
                error_count = len([d for d in result['adt_data'].values() 
                                 if 'error' in d])
                print(f"Processed ADTs: {adt_count}")
                print(f"Failed ADTs: {error_count}")
        
        print(f"\nResults stored in: {db_path}")
        print(f"Log file: {log_file}")
        
    except Exception as e:
        logger.error(f"Error analyzing map: {e}", exc_info=True)
        print(f"\nError: {e}")
        print(f"Check {log_file} for details")

def query_examples(db_path: str):
    """
    Examples of querying the database
    
    Args:
        db_path: Path to SQLite database
    """
    try:
        db = DatabaseManager(db_path)
        cursor = db.conn.cursor()
        
        print("\nDatabase Query Examples:")
        print("-" * 50)
        
        # Get WDT file info
        cursor.execute('''
            SELECT filepath, map_name, version, format, created_at
            FROM wdt_files
            ORDER BY created_at DESC
            LIMIT 1
        ''')
        wdt = cursor.fetchone()
        if wdt:
            print(f"\nLatest WDT File:")
            print(f"Path: {wdt[0]}")
            print(f"Map: {wdt[1]}")
            print(f"Version: {wdt[2]}")
            print(f"Format: {wdt[3]}")
            print(f"Analyzed: {wdt[4]}")
        
        # Count active tiles
        cursor.execute('''
            SELECT COUNT(*) 
            FROM map_tiles
            WHERE wdt_id = (
                SELECT id FROM wdt_files 
                ORDER BY created_at DESC 
                LIMIT 1
            )
        ''')
        tile_count = cursor.fetchone()[0]
        print(f"\nActive Tiles: {tile_count}")
        
        # Get texture statistics
        cursor.execute('''
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN has_alpha = 1 THEN 1 ELSE 0 END) as alpha,
                   SUM(CASE WHEN is_compressed = 1 THEN 1 ELSE 0 END) as compressed
            FROM wdt_textures
            WHERE wdt_id = (
                SELECT id FROM wdt_files 
                ORDER BY created_at DESC 
                LIMIT 1
            )
        ''')
        textures = cursor.fetchone()
        if textures:
            print(f"\nTexture Statistics:")
            print(f"Total Textures: {textures[0]}")
            print(f"With Alpha: {textures[1]}")
            print(f"Compressed: {textures[2]}")
        
        # Get model counts
        cursor.execute('''
            SELECT 
                (SELECT COUNT(*) FROM m2_models WHERE wdt_id = w.id) as m2_count,
                (SELECT COUNT(*) FROM wmo_models WHERE wdt_id = w.id) as wmo_count,
                (SELECT COUNT(*) FROM m2_placements WHERE wdt_id = w.id) as m2_placements,
                (SELECT COUNT(*) FROM wmo_placements WHERE wdt_id = w.id) as wmo_placements
            FROM wdt_files w
            ORDER BY created_at DESC
            LIMIT 1
        ''')
        models = cursor.fetchone()
        if models:
            print(f"\nModel Statistics:")
            print(f"M2 Models: {models[0]}")
            print(f"WMO Models: {models[1]}")
            print(f"M2 Placements: {models[2]}")
            print(f"WMO Placements: {models[3]}")
        
    except Exception as e:
        print(f"Error querying database: {e}")
    finally:
        if db:
            db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python example.py <path_to_wdt_file> [database_path] [adt_directory]")
        sys.exit(1)
    
    wdt_path = sys.argv[1]
    db_path = sys.argv[2] if len(sys.argv) > 2 else None
    adt_dir = sys.argv[3] if len(sys.argv) > 3 else None
    
    # Analyze map
    analyze_map(wdt_path, db_path, adt_dir)
    
    # Show query examples if database was created
    if db_path:
        query_examples(db_path)