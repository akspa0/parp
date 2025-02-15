"""MCLY (Texture Layer) chunk parser."""
from typing import Dict, Any, List
import struct
import logging
from ..base import BaseChunk, ChunkParsingError
from .entry import MclyEntry

logger = logging.getLogger(__name__)

class MclyChunk(BaseChunk):
    """MCLY (Texture Layer) chunk parser.
    
    Contains information about texture layers.
    Each entry is 16 bytes.
    """
    
    ENTRY_SIZE = 16
    
    def parse(self) -> Dict[str, Any]:
        """Parse MCLY chunk data.
        
        Returns:
            Dictionary containing:
            - layers: List of texture layer entries
            - count: Number of valid layers
            - error: Optional error message if chunk is malformed
        """
        # Handle empty chunks
        if not self.data:
            return {
                'layers': [],
                'count': 0,
                'error': 'Empty chunk data'
            }
        
        # Check if chunk size is valid
        if len(self.data) % self.ENTRY_SIZE != 0:
            logger.warning(
                f"MCLY chunk size {len(self.data)} not divisible by {self.ENTRY_SIZE}. "
                "Truncating to nearest valid size."
            )
            # Truncate data to nearest valid size
            valid_size = (len(self.data) // self.ENTRY_SIZE) * self.ENTRY_SIZE
            if valid_size == 0:
                return {
                    'layers': [],
                    'count': 0,
                    'error': f'Invalid chunk size: {len(self.data)}'
                }
            self.data = self.data[:valid_size]
        
        count = len(self.data) // self.ENTRY_SIZE
        entries = []
        
        for i in range(count):
            try:
                entry_data = self.data[i*self.ENTRY_SIZE:(i+1)*self.ENTRY_SIZE]
                
                # Unpack the entry
                texture_id, flags, mcal_offset, effect_id = struct.unpack('<4I', entry_data)
                
                entry = MclyEntry(
                    texture_id=texture_id,
                    flags=flags,
                    mcal_offset=mcal_offset,
                    effect_id=effect_id
                )
                entries.append(entry.to_dict())
                
            except Exception as e:
                logger.error(f"Failed to parse MCLY entry {i}: {e}")
                entries.append({
                    'error': str(e),
                    'texture_id': 0,
                    'flags': 0,
                    'mcal_offset': 0,
                    'effect_id': 0
                })
        
        return {
            'layers': entries,
            'count': len(entries),
            'valid_entries': len([e for e in entries if 'error' not in e])
        }