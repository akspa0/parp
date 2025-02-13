# adt_main.py
import os
import shutil
import logging
from datetime import datetime
from typing import Dict, Optional

from adt_core import ADTCoordinates, ADTOffsets
from adt_validator import NoggitADTValidator
from main_processor import ChunkProcessor

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
            current_coords = ADTCoordinates.from_filename(basename)
            if not current_coords:
                self.logger.error(f"Could not parse coordinates from {basename}")
                return False

            offset = ADTOffsets(
                x=new_coords.x - current_coords.x,
                y=new_coords.y - current_coords.y
            )

            with open(filepath, 'r+b') as f:
                processor = ChunkProcessor(f)
                processor.process_chunks(offset)

            # Post-validation
            validator = NoggitADTValidator(filepath)
            if not validator.validate():
                self.logger.error(f"Post-validation failed for {basename}:")
                for error in validator.get_errors():
                    self.logger.error(f"  {error}")
                self.logger.info("Restoring from backup")
                shutil.copy2(backup_path, filepath)
                return False

            # Move to target if needed
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