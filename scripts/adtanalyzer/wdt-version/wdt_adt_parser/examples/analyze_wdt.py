"""
Example script demonstrating how to use wdt_adt_parser to analyze WDT files.
"""
import sys
from pathlib import Path
import logging
from datetime import datetime

from wdt_adt_parser.universal_parser import create_parser
from wdt_adt_parser.database.manager import DatabaseManager

def setup_logging():
    """Setup logging configuration"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"parser_{timestamp}.log"
    
    # Configure file logging
    logging.basicConfig(
        filename=log_filename,
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Add console handler for important messages
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter('%(message)s'))
    logging.getLogger('').addHandler(console)
    
    return log_filename

def analyze_wdt(wdt_path: Path, db_path: Path):
    """
    Analyze a WDT file and store results in database
    
    Args:
        wdt_path: Path to WDT file
        db_path: Path to SQLite database file
    """
    log_file = setup_logging()
    logger = logging.getLogger('WDTAnalyzer')
    
    try:
        logger.info(f"\nAnalyzing WDT file: {wdt_path}")
        logger.info("=" * 50)
        
        # Create parser and database
        parser = create_parser()
        db = DatabaseManager(db_path)
        
        # Parse WDT file
        result = parser.parse_wdt(wdt_path)
        
        # Generate visualizations
        if 'visualizations' in result:
            vis_files = result['visualizations']
            logger.info("\nVisualizations generated:")
            for vis_type, vis_path in vis_files.items():
                logger.info(f"- {vis_type}: {vis_path}")
        
        # Log results
        logger.info("\nAnalysis Results:")
        logger.info(f"Format: {result['format']}")
        logger.info(f"Version: {result['version']}")
        logger.info(f"Active Tiles: {len(result.get('tiles', []))}")
        logger.info(f"M2 Models: {len(result.get('m2_models', []))}")
        logger.info(f"WMO Models: {len(result.get('wmo_models', []))}")
        
        if result.get('errors'):
            logger.warning("\nErrors encountered:")
            for error in result['errors']:
                logger.warning(f"- {error}")
        
        logger.info(f"\nResults stored in: {db_path}")
        logger.info(f"Log file: {log_file}")
        
    except Exception as e:
        logger.error(f"Error analyzing WDT file: {e}", exc_info=True)
        raise
    finally:
        if db:
            db.close()

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python analyze_wdt.py <path_to_wdt_file> [database_path]")
        sys.exit(1)
    
    wdt_path = Path(sys.argv[1])
    db_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("wdt_analysis.db")
    
    if not wdt_path.exists():
        print(f"Error: File {wdt_path} not found.")
        sys.exit(1)
    
    analyze_wdt(wdt_path, db_path)

if __name__ == '__main__':
    main()