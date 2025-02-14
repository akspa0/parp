# adt_analyzer/chunks/mwid/parser.py
from typing import Dict, Any, List
import struct
import logging
from ..base import BaseChunk, ChunkParsingError

logger = logging.getLogger(__name__)

class MwidChunk(BaseChunk):
    """MWID (WMO Indices) parser.
    
    Contains offsets into the MWMO chunk for WMO filenames.
    Each entry is a uint32 offset.
    Similar to MMID but for World Map Objects instead of M2 models.
    """
    
    def parse(self) -> Dict[str, Any]:
        """Parse MWID chunk data."""
        if len(self.data) % 4 != 0:
            raise ChunkParsingError(
                f"MWID chunk size {len(self.data)} not divisible by 4"
            )
        
        try:
            # Each entry is a uint32
            count = len(self.data) // 4
            offsets = []
            
            for i in range(count):
                offset = struct.unpack('<I', self.data[i*4:(i+1)*4])[0]
                offsets.append({
                    'index': i,
                    'offset': offset
                })
            
            return {
                'offsets': offsets,
                'count': count
            }
            
        except struct.error as e:
            raise ChunkParsingError(f"Failed to parse MWID data: {e}")
    
    def validate_against_mwmo(self, mwmo_data: Dict[str, Any]) -> List[str]:
        """Validate MWID offsets against MWMO chunk data."""
        errors = []
        mwmo_size = mwmo_data.get('data_size', 0)
        
        for entry in self.parse()['offsets']:
            offset = entry['offset']
            if offset >= mwmo_size:
                errors.append(
                    f"Offset {offset} at index {entry['index']} exceeds MWMO data size {mwmo_size}"
                )
        
        return errors

# Utility function for combining MWMO and MWID data
def combine_wmo_data(mwmo_data: Dict[str, Any], mwid_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Combine MWMO and MWID data to create a complete WMO list."""
    wmos = []
    mwmo_entries = {w['offset']: w['name'] for w in mwmo_data['wmos']}
    
    for entry in mwid_data['offsets']:
        offset = entry['offset']
        wmos.append({
            'index': entry['index'],
            'offset': offset,
            'name': mwmo_entries.get(offset, f"<invalid offset: {offset}>")
        })
    
    return wmos

if __name__ == "__main__":
    # Simple test data
    test_mwmo_data = b'Buildings/House01.wmo\0Dungeons/Cave01.wmo\0Props/Well01.wmo\0'
    test_mwid_data = struct.pack('<3I', 0, 21, 42)  # Offsets to each WMO name
    
    mwmo_chunk = MwmoChunk(header=None, data=test_mwmo_data)
    mwid_chunk = MwidChunk(header=None, data=test_mwid_data)
    
    mwmo_result = mwmo_chunk.parse()
    mwid_result = mwid_chunk.parse()
    
    # Combine the data
    wmos = combine_wmo_data(mwmo_result, mwid_result)
    
    print("Combined WMO data:")
    for wmo in wmos:
        print(f"  {wmo['index']}: {wmo['name']} (offset: {wmo['offset']})")
