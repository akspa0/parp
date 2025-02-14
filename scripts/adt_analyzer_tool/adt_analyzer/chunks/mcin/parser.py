# adt_analyzer/chunks/mcin/parser.py
from typing import Dict, Any, List
import logging
from ..base import BaseChunk, ChunkParsingError
from .entry import McinEntry

logger = logging.getLogger(__name__)

class McinChunk(BaseChunk):
    """MCIN (Map Chunk Index) parser.
    
    Contains an array of entries that provide offset and size information
    for each MCNK chunk in the ADT file.
    
    There are 256 entries (16x16 grid), each 16 bytes long.
    Total size should be 4096 bytes.
    """
    
    ENTRY_SIZE = 16
    TOTAL_ENTRIES = 256
    EXPECTED_SIZE = ENTRY_SIZE * TOTAL_ENTRIES
    
    def parse(self) -> Dict[str, Any]:
        """Parse MCIN chunk data."""
        if len(self.data) != self.EXPECTED_SIZE:
            raise ChunkParsingError(
                f"MCIN chunk size {len(self.data)} != {self.EXPECTED_SIZE}"
            )
        
        entries: List[Dict[str, Any]] = []
        mcnk_offsets: List[int] = []  # Keep track of MCNK offsets for validation
        
        for i in range(self.TOTAL_ENTRIES):
            try:
                entry_data = self.data[i * self.ENTRY_SIZE:(i + 1) * self.ENTRY_SIZE]
                entry = McinEntry.from_bytes(entry_data, i)
                
                # Basic validation
                if entry.offset > 0:  # Valid MCNK chunk
                    if entry.offset in mcnk_offsets:
                        logger.warning(f"Duplicate MCNK offset {entry.offset} in entry {i}")
                    mcnk_offsets.append(entry.offset)
                
                # Calculate grid position
                grid_x = i % 16
                grid_y = i // 16
                
                entry_dict = entry.to_dict()
                entry_dict.update({
                    'index': i,
                    'grid_position': (grid_x, grid_y)
                })
                entries.append(entry_dict)
                
            except Exception as e:
                logger.error(f"Error parsing MCIN entry {i}: {e}")
                # Add placeholder for failed entry
                entries.append({
                    'index': i,
                    'grid_position': (i % 16, i // 16),
                    'error': str(e)
                })
        
        return {
            'entries': entries,
            'count': len(entries),
            'valid_chunks': len([e for e in entries if 'error' not in e])
        }

# Example usage:
if __name__ == "__main__":
    # Simple test code
    import os
    
    def test_mcin_parser(file_path: str) -> None:
        """Test MCIN chunk parsing with a real ADT file."""
        with open(file_path, 'rb') as f:
            # Skip MVER chunk (8 bytes header + 4 bytes data)
            f.seek(12)
            # Skip MHDR chunk header (8 bytes)
            f.seek(8, 1)
            # Now at MCIN data
            mcin_data = f.read(4096)  # Read exact size
            
            chunk = McinChunk(header=None, data=mcin_data)
            result = chunk.parse()
            
            print(f"Parsed {result['count']} entries")
            print(f"Valid chunks: {result['valid_chunks']}")
            
            # Print first few entries
            for entry in result['entries'][:5]:
                print(f"Entry {entry['index']}: "
                      f"Position {entry['grid_position']}, "
                      f"Offset {entry.get('offset', 'ERROR')}")