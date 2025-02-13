# adt_fix.py
import os
import re
import shutil
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict
from dataclasses import asdict

from adt_core import ADTCoordinates, ADTOffsets
from adt_validator import NoggitADTValidator
from main_processor import ChunkProcessor
from logging_config import setup_logging

# In main script initialization
logger = setup_logging(log_dir='logs')

def analyze_adt_file(filepath: str) -> Dict:
    filename = os.path.basename(filepath)
    current_coords = ADTCoordinates.from_filename(filename)
    
    if not current_coords:
        return {
            'filename': filename,
            'status': 'error',
            'message': 'Could not parse current coordinates from filename'
        }

    # Parse coordinates from current file position
    match = re.match(r'.*?(\d+)_(\d+)\.adt$', filename)
    if not match:
        return {
            'filename': filename,
            'status': 'error',
            'message': 'Could not parse coordinates from filename'
        }
    
    x, y = int(match.group(1)), int(match.group(2))
    
    validator = NoggitADTValidator(filepath)
    if not validator.validate():
        return {
            'filename': filename,
            'status': 'error',
            'message': 'Failed validation',
            'errors': validator.get_errors()
        }

    return {
        'filename': filename,
        'status': 'ok',
        'current_x': x,
        'current_y': y,
        'needs_processing': True
    }

def fix_adt_files(source_dir: str, output_dir: Optional[str] = None, dry_run: bool = False):
    logger = logging.getLogger('ADTFixer')
    handler = logging.FileHandler(f'adt_fix_{Path(source_dir).name}.log')
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    results = []
    for filename in os.listdir(source_dir):
        if not filename.lower().endswith('.adt'):
            continue

        filepath = os.path.join(source_dir, filename)
        analysis = analyze_adt_file(filepath)
        
        if analysis['status'] == 'ok':
            if dry_run:
                results.append(analysis)
            else:
                try:
                    if output_dir:
                        os.makedirs(output_dir, exist_ok=True)
                        target_path = os.path.join(output_dir, filename)
                        shutil.copy2(filepath, target_path)
                        filepath = target_path

                    with open(filepath, 'r+b') as f:
                        processor = ChunkProcessor(f)
                        processor.process_chunks(ADTOffsets(
                            x=analysis['current_x'],
                            y=analysis['current_y']
                        ))

                    analysis['processed'] = True
                    results.append(analysis)

                except Exception as e:
                    analysis['status'] = 'error'
                    analysis['message'] = str(e)
                    results.append(analysis)
        else:
            results.append(analysis)

    if dry_run:
        print("\nAnalysis Results:")
        for result in results:
            if result['status'] == 'ok':
                print(f"\n{result['filename']}:")
                print(f"  Current position: ({result['current_x']}, {result['current_y']})")
                print(f"  Action: Would process this file")
            else:
                print(f"\n{result['filename']}: ERROR")
                print(f"  {result['message']}")
                if 'errors' in result:
                    for error in result['errors']:
                        print(f"  - {error}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Fix ADT chunk data for renamed files')
    parser.add_argument('source_dir', help='Directory containing ADT files')
    parser.add_argument('--output-dir', help='Output directory for processed files')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be done without making changes')
    args = parser.parse_args()
    
    fix_adt_files(args.source_dir, args.output_dir, args.dry_run)

if __name__ == '__main__':
    main()