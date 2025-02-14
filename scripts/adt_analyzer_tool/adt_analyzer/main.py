# main.py
import argparse
import logging
from pathlib import Path
import json
import sys

from adt_analyzer.parser import AdtFileParser
from adt_analyzer.utils.logging import setup_logging

def process_adt_files(
    directory: Path,
    output_dir: Path,
    listfile_path: Optional[Path] = None
) -> None:
    """Process all ADT files in directory."""
    parser = AdtFileParser()
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each ADT file
    for adt_file in directory.glob('*.adt'):
        try:
            logger.info(f"Processing {adt_file}")
            result = parser.parse_file(adt_file)
            
            # Save results to JSON
            output_path = output_dir / f"{adt_file.stem}_analysis.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
                
            logger.info(f"Results written to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to process {adt_file}: {e}")

def main():
    parser = argparse.ArgumentParser(
        description='Process ADT files and generate analysis files'
    )
    parser.add_argument('directory', 
                       help='Directory containing ADT files')
    parser.add_argument('--output',
                       default='output',
                       help='Output directory for analysis files')
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
    
    # Validate paths
    if not directory.is_dir():
        logger.error(f"Directory not found: {directory}")
        return 1
    
    if listfile_path and not listfile_path.is_file():
        logger.error(f"Listfile not found: {listfile_path}")
        return 1
    
    # Process files
    try:
        process_adt_files(directory, output_dir, listfile_path)
        logger.info("Processing complete")
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
