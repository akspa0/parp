# adt_analyzer/chunks/mddf/parser.py
from typing import Dict, Any, List
import logging
from ..base import BaseChunk, ChunkParsingError
from .entry import MddfEntry

logger = logging.getLogger(__name__)

class MddfChunk(BaseChunk):
    """MDDF (M2 Model Placement) chunk parser.
    
    Contains information about M2 model placement in the map.
    Each entry is 36 bytes.
    """
    
    ENTRY_SIZE = 36
    
    def parse(self) -> Dict[str, Any]:
        """Parse MDDF chunk data."""
        if len(self.data) % self.ENTRY_SIZE != 0:
            raise ChunkParsingError(
                f"MDDF chunk size {len(self.data)} not divisible by {self.ENTRY_SIZE}"
            )
        
        count = len(self.data) // self.ENTRY_SIZE
        entries = []
        
        for i in range(count):
            try:
                entry_data = self.data[i*self.ENTRY_SIZE:(i+1)*self.ENTRY_SIZE]
                entry = MddfEntry.from_bytes(entry_data)
                entries.append({
                    'index': i,
                    **entry.to_dict()
                })
                
            except Exception as e:
                logger.error(f"Failed to parse MDDF entry {i}: {e}")
                entries.append({
                    'index': i,
                    'error': str(e)
                })
        
        return {
            'entries': entries,
            'count': count,
            'valid_entries': len([e for e in entries if 'error' not in e])
        }
