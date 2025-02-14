# adt_analyzer/chunks/mcnk/water_parser.py
from typing import Dict, Any, Optional
import logging
from ..mh2o import Mh2oChunk
from ..mclq import MclqChunk

logger = logging.getLogger(__name__)

class WaterParser:
    """Handles parsing of water-related data in MCNK chunks."""
    
    def __init__(self, chunk_data: bytes):
        self.data = chunk_data

    def parse_water(self, flags: int, offset: int, size: int) -> Optional[Dict[str, Any]]:
        """Parse water data, handling both modern and legacy formats."""
        if offset == 0:
            return None

        try:
            # Check for modern water (MH2O)
            if flags & 0x02:
                chunk = Mh2oChunk(
                    header=Mh2oChunk.from_bytes(self.data[offset:]).header,
                    data=self.data[offset:]
                )
                return {
                    'type': 'mh2o',
                    'data': chunk.parse()
                }
            
            # Fall back to legacy water (MCLQ)
            elif size > 0:
                chunk = MclqChunk(
                    header=MclqChunk.from_bytes(self.data[offset:]).header,
                    data=self.data[offset:offset+size]
                )
                return {
                    'type': 'mclq',
                    'data': chunk.parse()
                }
            
        except Exception as e:
            logger.error(f"Failed to parse water data at offset {offset}: {e}")
            return None
