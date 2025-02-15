"""MWMO (WMO Filenames) chunk parser."""
from typing import Dict, Any
import struct
from ..base import BaseChunk, ChunkParsingError

class MwmoChunk(BaseChunk):
    """MWMO chunk parser.
    
    Contains a list of WMO filenames used in the ADT file.
    Each filename is null-terminated.
    """
    
    def parse(self) -> Dict[str, Any]:
        """Parse MWMO chunk data.
        
        Returns:
            Dictionary containing:
            - wmo_name_block: Raw data block containing null-terminated filenames
            - size: Size of the data block
        """
        return {
            'wmo_name_block': self.data,
            'size': len(self.data)
        }

    def parse_filenames(self) -> Dict[str, Any]:
        """Parse MWMO chunk data into structured format.
        
        Returns:
            Dictionary containing:
            - wmos: List of WMO entries with name, offset, and length
            - count: Number of WMOs
            - data_size: Total size of WMO name data
        """
        wmos = []
        offset = 0
        
        while offset < len(self.data):
            # Find end of current string
            end = self.data.find(b'\0', offset)
            if end == -1:
                break
                
            # Extract and decode filename
            name = self.data[offset:end].decode('utf-8')
            length = end - offset + 1  # Include null terminator
            
            wmos.append({
                'name': name,
                'offset': offset,
                'length': length
            })
            
            offset = end + 1
        
        return {
            'wmos': wmos,
            'count': len(wmos),
            'data_size': offset
        }
