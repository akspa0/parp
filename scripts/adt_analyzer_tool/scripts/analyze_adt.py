# scripts/analyze_adt.py (renamed from main.py)
import argparse
import logging
from pathlib import Path
import json
import sys
from typing import Optional, Dict, Any

# Add parent directory to Python path if running directly
if __name__ == "__main__":
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from adt_analyzer.parser import AdtFileParser
from adt_analyzer.utils.logging import setup_logging
from adt_analyzer.utils.db import DatabaseManager

def process_parser_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Process parser result to ensure correct data structure.
    
    Args:
        result: Raw parser result
        
    Returns:
        Processed result with consistent structure
    """
    processed = {
        'file_path': result.get('file_path', ''),
        'errors': result.get('errors', []),
        'chunks': {}
    }
    
    # Ensure chunks is a dictionary
    chunks = result.get('chunks', {})
    if isinstance(chunks, dict):
        processed['chunks'] = chunks
    else:
        logger.warning(f"Unexpected chunks format: {type(chunks)}")
        
    return processed

def process_adt_files(
    directory: Path,
    output_dir: Path,
    output_format: str = 'json',
    db_path: Optional[Path] = None,
    listfile_path: Optional[Path] = None
) -> None:
    """Process all ADT files in directory.
    
    Args:
        directory: Directory containing ADT files
        output_dir: Output directory for JSON files
        output_format: Output format ('json' or 'sqlite')
        db_path: Path to SQLite database (required if output_format is 'sqlite')
        listfile_path: Optional path to listfile for reference checking
    """
    parser = AdtFileParser()
    db_manager = None
    
    try:
        # Initialize database if using SQLite output
        if output_format == 'sqlite':
            if not db_path:
                raise ValueError("db_path is required for SQLite output")
            
            db_manager = DatabaseManager(db_path)
            db_manager.initialize()
            logger.info(f"Initialized SQLite database at {db_path}")
        
        # Create output directory for JSON files if needed
        if output_format == 'json':
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Process each ADT file
        for adt_file in directory.glob('*.adt'):
            try:
                logger.info(f"Processing {adt_file}")
                raw_result = parser.parse_file(adt_file)
                
                # Process result to ensure consistent structure
                result = process_parser_result(raw_result)
                
                if output_format == 'json':
                    # Save results to JSON
                    output_path = output_dir / f"{adt_file.stem}_analysis.json"
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(result, f, indent=2)
                    logger.info(f"Results written to {output_path}")
                else:
                    # Store results in database
                    db_manager.store_adt_file(adt_file.name, result)
                    logger.info(f"Results stored in database for {adt_file.name}")
                    
            except Exception as e:
                logger.error(f"Failed to process {adt_file}: {e}")
                if logger.isEnabledFor(logging.DEBUG):
                    logger.exception("Detailed error:")
                
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        if logger.isEnabledFor(logging.DEBUG):
            logger.exception("Detailed error:")
        raise
        
    finally:
        # Close database connection if it was opened
        if db_manager:
            db_manager.close()

def main():
    parser = argparse.ArgumentParser(
        description='Process ADT files and generate analysis files'
    )
    parser.add_argument('directory', 
                       help='Directory containing ADT files')
    parser.add_argument('--output',
                       default='output',
                       help='Output directory for JSON analysis files')
    parser.add_argument('--output-format',
                       choices=['json', 'sqlite'],
                       default='json',
                       help='Output format (json or sqlite)')
    parser.add_argument('--db-path',
                       help='Path to SQLite database (required if output-format is sqlite)')
    parser.add_argument('--listfile',
                       help='Path to listfile for reference checking')
    parser.add_argument('--log-dir',
                       default='logs',
                       help='Log directory')
    parser.add_argument('--verbose', '-v',
                       action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(args.log_dir, log_level)
    
    # Get logger after setup
    global logger
    logger = logging.getLogger(__name__)
    
    # Convert paths
    directory = Path(args.directory)
    output_dir = Path(args.output)
    listfile_path = Path(args.listfile) if args.listfile else None
    db_path = Path(args.db_path) if args.db_path else None
    
    # Validate paths
    if not directory.is_dir():
        logger.error(f"Directory not found: {directory}")
        return 1
    
    if listfile_path and not listfile_path.is_file():
        logger.error(f"Listfile not found: {listfile_path}")
        return 1
        
    # Validate SQLite arguments
    if args.output_format == 'sqlite' and not args.db_path:
        logger.error("--db-path is required when using --output-format sqlite")
        return 1
    
    # Process files
    try:
        process_adt_files(
            directory,
            output_dir,
            args.output_format,
            db_path,
            listfile_path
        )
        logger.info("Processing complete")
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        if logger.isEnabledFor(logging.DEBUG):
            logger.exception("Detailed error:")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
