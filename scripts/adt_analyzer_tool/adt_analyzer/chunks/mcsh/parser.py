from typing import Dict, Any, List
from ..base import BaseChunk, ChunkParsingError

class McshChunk(BaseChunk):
    """MCSH (Shadow Map) chunk parser.
    
    Contains shadow map information for the terrain chunk.
    The shadow map is a 64x64 grid where each byte represents
    the shadow intensity for a cell.
    """
    
    WIDTH = 64
    HEIGHT = 64
    EXPECTED_SIZE = WIDTH * HEIGHT
    
    def parse(self) -> Dict[str, Any]:
        """Parse MCSH chunk data.
        
        Returns:
            Dictionary containing:
            - shadow_map: List of shadow values (0-255)
            - dimensions: (width, height) of the shadow map
            - complete: Whether the shadow map is complete (correct size)
            
        Note:
            Some ADT files may contain incomplete shadow maps.
            In these cases, the available data is still returned
            but marked as incomplete.
        """
        shadow_data = list(self.data)
        is_complete = len(shadow_data) == self.EXPECTED_SIZE
        
        if not is_complete:
            # Log warning but don't raise error - partial data might still be useful
            from logging import getLogger
            logger = getLogger(__name__)
            logger.warning(
                f"MCSH chunk incomplete: {len(shadow_data)} != {self.EXPECTED_SIZE}"
            )
        
        return {
            'shadow_map': shadow_data,
            'dimensions': (self.WIDTH, self.HEIGHT),
            'complete': is_complete
        }