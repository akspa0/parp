import os
import shutil
from typing import Dict, Optional, List
import logging
from datetime import datetime

class ADTProcessor:
    def __init__(self, source_dir: str, target_dir: Optional[str] = None):
        self.source_dir = source_dir
        self.target_dir = target_dir or source_dir
        self._setup_logging()
        
    def _setup_logging(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logger = logging.getLogger('ADTProcessor')
        handler = logging.FileHandler(f'adt_processor_{timestamp}.log')
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def process_file(self, filepath: str, new_coords: ADTCoordinates) -> bool:
        basename = os.path.basename(filepath)
        self.logger.info(f"Processing {basename}")

        # Pre-validation
        validator = NoggitADTValidator(filepath)
        if not validator.validate():
            self.logger.error(f"Pre-validation failed for {basename}:")
            for error in validator.get_errors():
                self.logger.error(f"  {error}")
            return False

        # Create backup
        backup_path = f"{filepath}.{datetime.now():%Y%m%d_%H%M%S}.bak"
        shutil.copy2(filepath, backup_path)
        self.logger.info(f"Created backup at {backup_path}")

        try:
            # Apply changes
            patcher = ADTPatcher(filepath)
            current_coords = ADTCoordinates.from_filename(basename)
            if not current_coords:
                self.logger.error(f"Could not parse coordinates from {basename}")
                return False

            offset = ADTOffsets(
                x=new_coords.x - current_coords.x,
                y=new_coords.y - current_coords.y
            )
            patcher.update_offsets(offset)

            # Post-validation
            validator = NoggitADTValidator(filepath)
            if not validator.validate():
                self.logger.error(f"Post-validation failed for {basename}:")
                for error in validator.get_errors():
                    self.logger.error(f"  {error}")
                self.logger.info("Restoring from backup")
                shutil.copy2(backup_path, filepath)
                return False

            # Rename if needed
            if self.target_dir != self.source_dir:
                new_name = f"{basename[:-8]}_{new_coords.x}_{new_coords.y}.adt"
                target_path = os.path.join(self.target_dir, new_name)
                shutil.move(filepath, target_path)

            return True

        except Exception as e:
            self.logger.error(f"Error processing {basename}: {str(e)}")
            self.logger.info("Restoring from backup")
            shutil.copy2(backup_path, filepath)
            return False

    def process_directory(self, new_coordinates: Dict[str, ADTCoordinates]) -> bool:
        os.makedirs(self.target_dir, exist_ok=True)
        
        success = True
        for filename in os.listdir(self.source_dir):
            if not filename.endswith('.adt'):
                continue
                
            if filename not in new_coordinates:
                self.logger.warning(f"No new coordinates for {filename}, skipping")
                continue
                
            filepath = os.path.join(self.source_dir, filename)
            if not self.process_file(filepath, new_coordinates[filename]):
                success = False

        return success

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Process ADT files')
    parser.add_argument('source_dir', help='Source directory containing ADT files')
    parser.add_argument('target_dir', help='Target coordinates reference directory')
    parser.add_argument('--output', help='Output directory for processed files')
    
    args = parser.parse_args()
    
    processor = ADTProcessor(args.source_dir, args.output)
    coordinates = generate_coordinate_mapping(args.source_dir, args.target_dir)
    
    if processor.process_directory(coordinates):
        print("Processing completed successfully")
        return 0
    else:
        print("Processing completed with errors. Check the log file.")
        return 1

if __name__ == '__main__':
    exit(main())
