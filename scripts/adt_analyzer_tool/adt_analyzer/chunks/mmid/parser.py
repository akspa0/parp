# adt_analyzer/chunks/mmid/parser.py
from typing import Dict, Any, List
import struct
import logging
from ..base import BaseChunk, ChunkParsingError

logger = logging.getLogger(__name__)

class MmidChunk(BaseChunk):
    """MMID (Model Indices) parser.
    
    Contains offsets into the MMDX chunk for model filenames.
    Each entry is a uint32 offset.
    """
    
    def parse(self) -> Dict[str, Any]:
        """Parse MMID chunk data."""
        if len(self.data) % 4 != 0:
            raise ChunkParsingError(
                f"MMID chunk size {len(self.data)} not divisible by 4"
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
            raise ChunkParsingError(f"Failed to parse MMID data: {e}")
    
    def validate_against_mmdx(self, mmdx_data: Dict[str, Any]) -> List[str]:
        """Validate MMID offsets against MMDX chunk data."""
        errors = []
        mmdx_size = mmdx_data.get('data_size', 0)
        
        for entry in self.parse()['offsets']:
            offset = entry['offset']
            if offset >= mmdx_size:
                errors.append(
                    f"Offset {offset} at index {entry['index']} exceeds MMDX data size {mmdx_size}"
                )
        
        return errors

# Example of combining MMDX and MMID data:
def combine_model_data(mmdx_data: Dict[str, Any], mmid_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Combine MMDX and MMID data to create a complete model list."""
    models = []
    mmdx_models = {m['offset']: m['name'] for m in mmdx_data['models']}
    
    for entry in mmid_data['offsets']:
        offset = entry['offset']
        models.append({
            'index': entry['index'],
            'offset': offset,
            'name': mmdx_models.get(offset, f"<invalid offset: {offset}>")
        })
    
    return models

if __name__ == "__main__":
    # Simple test data
    test_mmdx_data = b'Tree01.m2\0Rock01.m2\0Bush01.m2\0'
    test_mmid_data = struct.pack('<3I', 0, 9, 19)  # Offsets to each model name
    
    mmdx_chunk = MmdxChunk(header=None, data=test_mmdx_data)
    mmid_chunk = MmidChunk(header=None, data=test_mmid_data)
    
    mmdx_result = mmdx_chunk.parse()
    mmid_result = mmid_chunk.parse()
    
    # Combine the data
    models = combine_model_data(mmdx_result, mmid_result)
    
    print("Combined model data:")
    for model in models:
        print(f"  {model['index']}: {model['name']} (offset: {model['offset']})")
