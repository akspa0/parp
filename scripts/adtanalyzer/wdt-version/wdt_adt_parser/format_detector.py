"""
Format detection for WDT/ADT files.
"""
from enum import Enum, auto
from pathlib import Path
import mmap
import struct
import logging
from typing import Literal


class FileFormat(Enum):
    """Supported file formats"""
    ALPHA = auto()
    RETAIL = auto()

class FormatDetector:
    """Detects file format based on chunk signatures"""
    
    def __init__(self):
        """Initialize format detector"""
        self.logger = logging.getLogger('FormatDetector')
        self.reverse_names = False
    
    def _detect_name_reversal(self, mm: mmap.mmap) -> bool:
        """
        Detect if chunk names need to be reversed
        
        Args:
            mm: Memory-mapped file
            
        Returns:
            True if names need to be reversed, False otherwise
        """
        pos = 0
        while pos + 8 <= len(mm):
            magic = mm[pos:pos+4]
            if magic in [b'MVER', b'MPHD', b'MAIN']:
                return False
            if magic[::-1] in [b'MVER', b'MPHD', b'MAIN']:
                return True
            size = struct.unpack('<I', mm[pos+4:pos+8])[0]
            pos += 8 + size
        
        self.logger.warning("Could not definitively detect chunk name orientation")
        return False
    
    def detect_format(self, file_path: str | Path) -> FileFormat:
        """
        Detect file format based on chunk signatures
        
        Args:
            file_path: Path to file to analyze
            
        Returns:
            FileFormat enum indicating detected format
            
        Raises:
            FileNotFoundError: If file does not exist
            IOError: If file cannot be opened
            ValueError: If format cannot be determined
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, 'rb') as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                # First detect if chunk names need to be reversed
                self.reverse_names = self._detect_name_reversal(mm)
                
                # Look for format-specific chunks
                pos = 0
                found_alpha = False
                found_retail = False
                
                while pos + 8 <= len(mm):
                    magic_raw = mm[pos:pos+4]
                    magic = magic_raw[::-1] if self.reverse_names else magic_raw
                    magic_str = magic.decode('ascii', 'ignore')
                    size = struct.unpack('<I', mm[pos+4:pos+8])[0]
                    
                    # Alpha format indicators
                    if magic_str in ['MDNM', 'MONM']:
                        found_alpha = True
                        break
                    
                    # Retail format indicators
                    if magic_str in ['MMDX', 'MWMO']:
                        found_retail = True
                        break
                    
                    pos += 8 + size
                
                if found_alpha:
                    self.logger.info("Detected Alpha format")
                    return FileFormat.ALPHA
                elif found_retail:
                    self.logger.info("Detected Retail format")
                    return FileFormat.RETAIL
                
                # If no definitive indicators found, check for Alpha-specific MCNK structure
                pos = 0
                while pos + 8 <= len(mm):
                    magic_raw = mm[pos:pos+4]
                    magic = magic_raw[::-1] if self.reverse_names else magic_raw
                    magic_str = magic.decode('ascii', 'ignore')
                    size = struct.unpack('<I', mm[pos+4:pos+8])[0]
                    
                    if magic_str == 'MCNK':
                        # Check for Alpha MCNK header size (16 bytes)
                        if size >= 16:
                            data = mm[pos+8:pos+24]  # Get first 16 bytes of MCNK data
                            flags, area_id, n_layers, n_doodad_refs = struct.unpack('<4I', data)
                            # Alpha format has simpler flags and smaller header
                            if flags < 0x1000 and n_layers < 8:  # Typical Alpha values
                                self.logger.info("Detected Alpha format (based on MCNK structure)")
                                return FileFormat.ALPHA
                        break
                    
                    pos += 8 + size
                
                # Default to Retail if no Alpha indicators found
                self.logger.info("Defaulting to Retail format")
                return FileFormat.RETAIL
                
            finally:
                mm.close()

def detect_format(file_path: str | Path) -> Literal['alpha', 'retail']:
    """
    Helper function to detect file format
    
    Args:
        file_path: Path to file to analyze
        
    Returns:
        'alpha' or 'retail' string indicating the detected format
    """
    detector = FormatDetector()
    format_type = detector.detect_format(file_path)
    return 'alpha' if format_type == FileFormat.ALPHA else 'retail'