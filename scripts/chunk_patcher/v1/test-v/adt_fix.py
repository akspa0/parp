# adt_fix.py
import os
import re
import logging
from pathlib import Path
from typing import Optional, Tuple

from adt_core import ADTCoordinates, ADTOffsets
from adt_validator import NoggitADTValidator
from main_processor import ChunkProcessor

def get_original_coords(filename: str) -> Optional[Tuple[int, int]]:
    """Extract original coordinates from ADT filename based on patterns like:
    - 'original_32_48_moved_to_35_50.adt'
    - '32_48_to_35_50.adt'
    - 'old_32_48.adt'
    """
    patterns = [
        r'original_(\d+)_(\d+)_moved',
        r'(\d+)_(\d+)_to_',
        r'old_(\d+)_(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            return int(match.group(1)), int(match.group(2))
    return None

def fix_adt_files(directory: str, dry_run: bool = False):
    logger = logging.getLogger('ADTFixer')
    handler = logging.FileHandler(f'adt_fix_{Path(directory).name}.log')
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    for filename in os.listdir(directory):
        if not filename.lower().endswith('.adt'):
            continue

        filepath = os.path.join(directory, filename)
        logger.info(f"Processing {filename}")

        # Get current coordinates from filename
        current_coords = ADTCoordinates.from_filename(filename)
        if not current_coords:
            logger.error(f"Could not parse current coordinates from {filename}")
            continue

        # Get original coordinates from filename patterns
        original_coords = get_original_coords(filename)
        if not original_coords:
            logger.info(f"No original coordinates found in {filename}, skipping")
            continue

        # Calculate offset
        offset = ADTOffsets(
            x=current_coords.x - original_coords[0],
            y=current_coords.y - original_coords[1]
        )

        if dry_run:
            logger.info(f"Would fix {filename}: offset ({offset.x}, {offset.y})")
            continue

        # Validate, process, and validate again
        validator = NoggitADTValidator(filepath)
        if not validator.validate():
            logger.error(f"Pre-validation failed for {filename}")
            continue

        try:
            with open(filepath, 'r+b') as f:
                processor = ChunkProcessor(f)
                processor.process_chunks(offset)

            if not validator.validate():
                logger.error(f"Post-validation failed for {filename}")
                continue

            logger.info(f"Successfully processed {filename}")

        except Exception as e:
            logger.error(f"Error processing {filename}: {str(e)}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Fix ADT chunk data for renamed files')
    parser.add_argument('directory', help='Directory containing renamed ADT files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    args = parser.parse_args()
    
    fix_adt_files(args.directory, args.dry_run)

if __name__ == '__main__':
    main()