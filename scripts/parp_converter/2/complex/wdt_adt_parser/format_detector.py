"""
Format detection module for WDT/ADT files.
Detects file format (Alpha vs Retail) based on chunk signatures.
"""
import struct
from enum import Enum, auto
from pathlib import Path
import mmap
import logging

class FileFormat(Enum):
    """Enumeration of supported file formats"""
    ALPHA = auto()
    RETAIL = auto()

class FormatDetector:
    """Detects WDT/ADT file format based on chunk signatures"""
    
    # Chunk signatures that indicate specific formats
    ALPHA_SIGNATURES = {'MDNM', 'MONM'}  # Model/Object Name chunks in Alpha
    RETAIL_SIGNATURES = {'MMDX', 'MWMO'}  # Model/WMO Name chunks in Retail
    
    def __init__(self):
        self.logger = logging.getLogger('FormatDetector')
    
    def detect_format(self, file_path: str | Path) -> FileFormat:
        """
        Detect the format of a WDT/ADT file by scanning for format-specific signatures.
        
        Args:
            file_path: Path to the WDT/ADT file
            
        Returns:
            FileFormat enum indicating detected format (ALPHA or RETAIL)
            
        Raises:
            ValueError: If format cannot be definitively determined
            FileNotFoundError: If file does not exist
            IOError: If file cannot be read
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        try:
            with open(file_path, 'rb') as f:
                # Memory map the file for efficient chunk scanning
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    # Track found signatures
                    found_alpha = False
                    found_retail = False
                    version = None
                    
                    # Scan chunks
                    pos = 0
                    while pos < len(mm):
                        if pos + 8 > len(mm):
                            break
                            
                        # Read chunk header
                        chunk_name = mm[pos:pos+4].decode('ascii', 'ignore')
                        chunk_size = struct.unpack('<I', mm[pos+4:pos+8])[0]
                        
                        # Check for version first
                        if chunk_name == 'MVER':
                            version = struct.unpack('<I', mm[pos+8:pos+12])[0]
                            self.logger.info(f"Detected version: {version}")
                        
                        # Check format signatures
                        chunk_name = chunk_name[::-1]  # Reverse for correct order
                        if chunk_name in self.ALPHA_SIGNATURES:
                            found_alpha = True
                        elif chunk_name in self.RETAIL_SIGNATURES:
                            found_retail = True
                            
                        # Early return if we've found definitive signatures
                        if found_alpha and not found_retail:
                            self.logger.info("Detected Alpha format")
                            return FileFormat.ALPHA
                        elif found_retail and not found_alpha:
                            self.logger.info("Detected Retail format")
                            return FileFormat.RETAIL
                            
                        pos += 8 + chunk_size
                    
                    # Make final determination
                    if found_alpha and found_retail:
                        raise ValueError("File contains both Alpha and Retail signatures")
                    elif found_alpha:
                        return FileFormat.ALPHA
                    elif found_retail:
                        return FileFormat.RETAIL
                    else:
                        raise ValueError("Could not determine file format - no format-specific signatures found")
                        
        except IOError as e:
            raise IOError(f"Error reading file {file_path}: {e}")