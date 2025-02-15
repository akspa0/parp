"""MCSH (Shadow Map) chunk parser."""
from typing import Dict, Any, List, Tuple
import logging
from ..base import BaseChunk, ChunkParsingError

logger = logging.getLogger(__name__)

class McshChunk(BaseChunk):
    """MCSH (Shadow Map) chunk parser.
    
    Contains shadow map data for terrain.
    Expected size is 64x64 = 4096 bytes.
    """
    
    EXPECTED_SIZE = 64 * 64  # 64x64 shadow map
    
    def parse(self) -> Dict[str, Any]:
        """Parse MCSH chunk data.
        
        Returns:
            Dictionary containing:
            - shadow_map: List of shadow values (0-255)
            - dimensions: Tuple of (width, height)
            - complete: True if shadow map is complete
        """
        # Handle empty chunks
        if not self.data:
            return {
                'shadow_map': [0] * self.EXPECTED_SIZE,
                'dimensions': (64, 64),
                'complete': False
            }
        
        # Check if shadow map is complete
        if len(self.data) != self.EXPECTED_SIZE:
            logger.warning(f"MCSH chunk incomplete: {len(self.data)} != {self.EXPECTED_SIZE}")
            # Pad with zeros if too small
            if len(self.data) < self.EXPECTED_SIZE:
                shadow_map = list(self.data) + [0] * (self.EXPECTED_SIZE - len(self.data))
            else:
                # Truncate if too large
                shadow_map = list(self.data[:self.EXPECTED_SIZE])
        else:
            shadow_map = list(self.data)
        
        return {
            'shadow_map': shadow_map,
            'dimensions': (64, 64),
            'complete': len(self.data) == self.EXPECTED_SIZE
        }