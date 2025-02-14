# adt_analyzer/chunks/mcnk/parser.py
from typing import Dict, Any
import logging
from ..base import BaseChunk, ChunkParsingError
from .header import McnkHeader
from .subchunk_parser import SubchunkParser
from .water_parser import WaterParser
from ..mcvt import McvtChunk
from ..mcnr import McnrChunk
from ..mcrf import McrfChunk
from ..mcsh import McshChunk
from ..mccv import MccvChunk
from ..mclv import MclvChunk
from ..mcse import McseChunk

logger = logging.getLogger(__name__)

class McnkChunk(BaseChunk):
    """MCNK (Map Chunk) parser.
    
    Coordinates parsing of all sub-components of an MCNK chunk.
    """

    HEADER_SIZE = 128

    def parse(self) -> Dict[str, Any]:
        """Parse MCNK chunk and all its sub-chunks."""
        if len(self.data) < self.HEADER_SIZE:
            raise ChunkParsingError(
                f"MCNK chunk too small: {len(self.data)} < {self.HEADER_SIZE}"
            )

        # Parse header
        header = McnkHeader.from_bytes(self.data)
        result = {
            'header': {
                'flags': header.flags,
                'position': (header.ix, header.iy),
                'area_id': header.area_id,
                'holes': header.holes,
                'world_position': header.pos
            }
        }

        # Setup parsers
        subchunk_parser = SubchunkParser(self.data)
        water_parser = WaterParser(self.data)

        # Parse independent sub-chunks
        sub_chunks = {
            'mcvt': (McvtChunk, header.offset_mcvt),
            'mcnr': (McnrChunk, header.offset_mcnr),
            'mcrf': (McrfChunk, header.offset_mcrf),
            'mcsh': (McshChunk, header.offset_mcsh, header.size_mcsh),
            'mccv': (MccvChunk, header.offset_mccv),
            'mclv': (MclvChunk, header.offset_mclv),
            'mcse': (McseChunk, header.offset_mcse)
        }

        for name, params in sub_chunks.items():
            chunk_class = params[0]
            offset = params[1]
            size = params[2] if len(params) > 2 else None
            
            if parsed := subchunk_parser.parse_subchunk(chunk_class, offset, size):
                result[name] = parsed

        # Parse texture layers
        texture_data = subchunk_parser.parse_texture_layers(
            header.offset_mcly,
            header.offset_mcal,
            header.size_mcal
        )
        result.update(texture_data)

        # Parse water data
        if water_data := water_parser.parse_water(
            header.flags,
            header.offset_mclq,
            header.size_mclq
        ):
            result['water'] = water_data

        return result
