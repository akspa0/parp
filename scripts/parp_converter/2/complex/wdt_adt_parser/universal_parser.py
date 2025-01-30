"""
Universal parser interface for WDT/ADT files.
Detects format and uses appropriate parser implementation.
"""
from typing import Dict, Any, Optional, Union, List
from pathlib import Path
import logging
from datetime import datetime

from .format_detector import FormatDetector, FileFormat
from .formats.alpha.wdt_parser import AlphaWDTParser
from .formats.alpha.adt_parser import AlphaADTParser
from .formats.retail.wdt_parser import RetailWDTParser
from .formats.retail.adt_parser import RetailADTParser
from .base.wdt_parser import MapTile
from .database import DatabaseManager

class UniversalParser:
    """Universal parser for WDT/ADT files"""
    
    def __init__(self):
        """Initialize the universal parser"""
        self.logger = logging.getLogger('UniversalParser')
        self.format_detector = FormatDetector()
        self.wdt_parser: Optional[Union[AlphaWDTParser, RetailWDTParser]] = None
        self.adt_parser: Optional[Union[AlphaADTParser, RetailADTParser]] = None
        self.detected_format: Optional[FileFormat] = None
        self.db: Optional[DatabaseManager] = None
        self.wdt_id: Optional[int] = None
        
        # Configure logging
        self.setup_logging()
    
    def setup_logging(self):
        """Configure logging with timestamp-based filenames"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"parser_{timestamp}.log"
        
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.logger.setLevel(logging.DEBUG)
    
    def _create_wdt_parser(self, file_format: FileFormat) -> Union[AlphaWDTParser, RetailWDTParser]:
        """Create appropriate WDT parser based on detected format"""
        if file_format == FileFormat.ALPHA:
            parser = AlphaWDTParser()
        elif file_format == FileFormat.RETAIL:
            parser = RetailWDTParser()
        else:
            raise ValueError(f"Unsupported format: {file_format}")
        
        # Pass database connection if available
        if self.db:
            parser.db = self.db
            parser.wdt_id = self.wdt_id
        
        return parser
    
    def _create_adt_parser(self, file_format: FileFormat) -> Union[AlphaADTParser, RetailADTParser]:
        """Create appropriate ADT parser based on detected format"""
        if file_format == FileFormat.ALPHA:
            parser = AlphaADTParser()
        elif file_format == FileFormat.RETAIL:
            parser = RetailADTParser()
        else:
            raise ValueError(f"Unsupported format: {file_format}")
        
        # Pass database connection if available
        if self.db:
            parser.db = self.db
            parser.wdt_id = self.wdt_id
        
        return parser
    
    def initialize_database(self, db_path: Union[str, Path]) -> None:
        """Initialize database connection"""
        try:
            self.db = DatabaseManager(db_path)
            self.logger.info(f"Database initialized: {db_path}")
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def set_database(self, db: DatabaseManager, wdt_id: Optional[int] = None):
        """Set database connection for storing parsed data"""
        self.db = db
        self.wdt_id = wdt_id
        
        # Update existing parsers if any
        if self.wdt_parser:
            self.wdt_parser.db = db
            self.wdt_parser.wdt_id = wdt_id
        if self.adt_parser:
            self.adt_parser.db = db
            self.adt_parser.wdt_id = wdt_id
    
    def parse_wdt(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Parse a WDT file
        
        Args:
            file_path: Path to WDT file
            
        Returns:
            Dictionary containing parsed WDT data
            
        Raises:
            ValueError: If format cannot be detected or file is invalid
            FileNotFoundError: If file does not exist
            IOError: If file cannot be read
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            # Detect format
            self.detected_format = self.format_detector.detect_format(file_path)
            self.logger.info(f"Detected {self.detected_format.name} format")
            
            # Create and use appropriate parser
            self.wdt_parser = self._create_wdt_parser(self.detected_format)
            self.wdt_parser.open(file_path)
            result = self.wdt_parser.parse()
            
            # Add format information
            result['format'] = self.detected_format.name.lower()
            
            # Store WDT record in database if connected
            if self.db and not self.wdt_id:
                try:
                    self.wdt_id = self.db.insert_wdt_record(
                        str(file_path),
                        file_path.stem,
                        result.get('version'),
                        result.get('flags'),
                        result.get('is_wmo_based', False),
                        result.get('chunk_order', ''),
                        result['format']
                    )
                    self.logger.info(f"Stored WDT record with ID: {self.wdt_id}")
                    
                    # Update parsers with new WDT ID
                    self.wdt_parser.wdt_id = self.wdt_id
                    if self.adt_parser:
                        self.adt_parser.wdt_id = self.wdt_id
                        
                except Exception as e:
                    self.logger.error(f"Failed to store WDT record: {e}")
                    raise
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing WDT file: {e}")
            raise
        finally:
            if self.wdt_parser:
                self.wdt_parser.close()
    
    def parse_adt(self, file_path: Union[str, Path], tile_x: int = -1, tile_y: int = -1) -> Dict[str, Any]:
        """
        Parse an ADT file
        
        Args:
            file_path: Path to ADT file
            tile_x: Optional X coordinate of tile
            tile_y: Optional Y coordinate of tile
            
        Returns:
            Dictionary containing parsed ADT data
            
        Raises:
            ValueError: If format cannot be detected or file is invalid
            FileNotFoundError: If file does not exist
            IOError: If file cannot be read
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            # Detect format if not already detected
            if not self.detected_format:
                self.detected_format = self.format_detector.detect_format(file_path)
                self.logger.info(f"Detected {self.detected_format.name} format")
            
            # Create and use appropriate parser
            self.adt_parser = self._create_adt_parser(self.detected_format)
            self.adt_parser.open(file_path)
            result = self.adt_parser.parse()
            
            # Add format and coordinate information
            result.update({
                'format': self.detected_format.name.lower(),
                'coordinates': {'x': tile_x, 'y': tile_y}
            })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing ADT file: {e}")
            raise
        finally:
            if self.adt_parser:
                self.adt_parser.close()
    
    def parse_map(self, wdt_path: Union[str, Path], adt_dir: Optional[Union[str, Path]] = None,
                 db_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """
        Parse a complete map (WDT + ADTs)
        
        Args:
            wdt_path: Path to WDT file
            adt_dir: Optional directory containing ADT files. If not provided,
                    will look in same directory as WDT
            db_path: Optional path to SQLite database for storing results
            
        Returns:
            Dictionary containing complete map data
            
        Raises:
            ValueError: If format cannot be detected or files are invalid
            FileNotFoundError: If files do not exist
            IOError: If files cannot be read
        """
        wdt_path = Path(wdt_path)
        if adt_dir:
            adt_dir = Path(adt_dir)
        else:
            adt_dir = wdt_path.parent
            
        # Initialize database if path provided
        if db_path:
            self.initialize_database(db_path)
        
        try:
            # Parse WDT first
            self.logger.info(f"Parsing WDT file: {wdt_path}")
            wdt_data = self.parse_wdt(wdt_path)
            
            # Add ADT data if available
            if 'tiles' in wdt_data:
                adt_data = {}
                total_tiles = len([t for t in wdt_data['tiles'] 
                                 if t.get('flags_decoded', {}).get('has_adt')])
                processed = 0
                errors = 0
                
                self.logger.info(f"Found {total_tiles} tiles with ADT data")
                
                for tile in wdt_data['tiles']:
                    if not tile.get('flags_decoded', {}).get('has_adt'):
                        continue
                        
                    x, y = tile['coordinates']['x'], tile['coordinates']['y']
                    adt_name = f"{wdt_path.stem}_{x}_{y}.adt"
                    adt_path = adt_dir / adt_name
                    
                    processed += 1
                    if processed % 10 == 0:
                        self.logger.info(
                            f"Processing tiles: {processed}/{total_tiles} "
                            f"({errors} errors)"
                        )
                    
                    if adt_path.exists():
                        try:
                            adt_data[f"{x}_{y}"] = self.parse_adt(adt_path, x, y)
                        except Exception as e:
                            errors += 1
                            self.logger.error(f"Error parsing ADT at ({x}, {y}): {e}")
                            adt_data[f"{x}_{y}"] = {'error': str(e)}
                    else:
                        self.logger.warning(f"ADT file not found: {adt_path}")
                
                self.logger.info(
                    f"Completed processing {processed} tiles with {errors} errors"
                )
                wdt_data['adt_data'] = adt_data
            
            return wdt_data
            
        except Exception as e:
            self.logger.error(f"Error parsing map: {e}")
            raise
        finally:
            # Clean up database connection
            if self.db:
                self.db.close()
                self.db = None
                self.wdt_id = None

def create_parser() -> UniversalParser:
    """Create a new universal parser instance"""
    return UniversalParser()