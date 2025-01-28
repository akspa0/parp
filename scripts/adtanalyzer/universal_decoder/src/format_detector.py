"""
Format detection for WoW map files
"""

import struct
from enum import Enum, auto
from pathlib import Path
from typing import Tuple

class FileFormat(Enum):
    """Supported file formats"""
    ALPHA = auto()
    RETAIL = auto()

class FileType(Enum):
    """Supported file types"""
    WDT = auto()
    ADT = auto()

class FormatDetector:
    """Detects file format and type for WoW map files"""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        
    def detect_format(self) -> Tuple[FileType, FileFormat, bool]:
        """
        Detect file format and type
        
        Returns:
            Tuple of (FileType, FileFormat, reversed_chunks)
        """
        # Determine file type from extension
        file_type = self._detect_file_type()
        
        # Read file header
        with open(self.file_path, 'rb') as f:
            data = f.read(1024)  # Read first 1KB for analysis
            
        # Try both normal and reversed chunk names
        normal_chunks = self._try_parse_chunks(data, reverse_names=False)
        reversed_chunks = self._try_parse_chunks(data, reverse_names=True)
        
        # Check which orientation has known chunks
        normal_known = any(c[0] in [b'MVER', b'MPHD', b'MAIN', b'MDNM', b'MONM'] for c in normal_chunks)
        reversed_known = any(c[0] in [b'MVER', b'MPHD', b'MAIN', b'MDNM', b'MONM'] for c in reversed_chunks)
        
        # Determine chunk name orientation
        chunks_reversed = reversed_known and not normal_known
        
        # Get chunks in correct orientation
        chunks = reversed_chunks if chunks_reversed else normal_chunks
        
        # Detect format based on chunk patterns and sizes
        format_type = self._detect_format_from_chunks(chunks, file_type)
        
        return file_type, format_type, chunks_reversed
        
    def _detect_file_type(self) -> FileType:
        """Detect file type from extension"""
        ext = self.file_path.suffix.lower()
        if ext == '.wdt':
            return FileType.WDT
        elif ext == '.adt':
            return FileType.ADT
        else:
            raise ValueError(f"Unsupported file extension: {ext}")
            
    def _try_parse_chunks(self, data: bytes, reverse_names: bool = False) -> list:
        """Try to parse chunks with given name orientation"""
        chunks = []
        pos = 0
        size = len(data)
        
        while pos + 8 <= size:
            chunk_name = data[pos:pos+4]
            if reverse_names:
                chunk_name = chunk_name[::-1]
                
            chunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]
            
            if pos + 8 + chunk_size > size:
                break
                
            chunk_data = data[pos+8:pos+8+chunk_size]
            chunks.append((chunk_name, chunk_data, chunk_size))
            
            pos += 8 + chunk_size
            if len(chunks) > 10:  # Only need first few chunks
                break
                
        return chunks
        
    def _detect_format_from_chunks(self, chunks: list, file_type: FileType) -> FileFormat:
        """
        Detect format based on chunk patterns and sizes
        
        For WDT files:
        - Alpha: MPHD is 128 bytes, has MDNM/MONM chunks
        - Retail: MPHD is 32 bytes, has MMDX/MWMO chunks
        
        For ADT files:
        - Alpha: Has MDNM/MONM chunks
        - Retail: Has MMDX/MMID/MWMO/MWID chunks
        """
        # First check for version
        for chunk_name, chunk_data, _ in chunks:
            if chunk_name == b'MVER':
                version = struct.unpack('<I', chunk_data)[0]
                if version < 18:
                    return FileFormat.ALPHA
        
        # For WDT files, check MPHD size
        if file_type == FileType.WDT:
            for chunk_name, _, chunk_size in chunks:
                if chunk_name == b'MPHD':
                    if chunk_size == 128:
                        return FileFormat.ALPHA
                    elif chunk_size == 32:
                        return FileFormat.RETAIL
        
        # Look for format-specific chunks
        has_alpha_chunks = any(c[0] in [b'MDNM', b'MONM', b'MAOC', b'MAOF'] for c in chunks)
        has_retail_chunks = any(c[0] in [b'MMDX', b'MMID', b'MWMO', b'MWID'] for c in chunks)
        
        if has_alpha_chunks and not has_retail_chunks:
            return FileFormat.ALPHA
        elif has_retail_chunks and not has_alpha_chunks:
            return FileFormat.RETAIL
            
        # If we can't definitively determine, look at the file path
        # Alpha client files often have specific paths
        path_str = str(self.file_path).lower()
        if any(x in path_str for x in ['053-client', 'alpha', '0.5.3']):
            return FileFormat.ALPHA
            
        # Default to Retail if we can't determine
        return FileFormat.RETAIL