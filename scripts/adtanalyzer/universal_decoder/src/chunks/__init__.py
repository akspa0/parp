"""
Chunk decoders and registry for WoW map file formats
"""

from .registry import ChunkRegistry, ChunkFormat, chunk_registry
from .common.base_decoder import ChunkDecoder, Vector3D
from .common.basic_chunks import MVERDecoder, MTEXDecoder
from .common.map_chunks import (
    MPHDDecoder, MAINDecoder, MDDFDecoder, MODFDecoder,
    MMDXDecoder, MMIDDecoder, MWMODecoder, MWIDDecoder
)
from .common.terrain_chunks import (
    MCNKDecoder, MCVTDecoder, MCNRDecoder, MCLYDecoder,
    MCALDecoder, MCSHDecoder, MCLQDecoder, MCCVDecoder
)
from .alpha.map_chunks import (
    AlphaMPHDDecoder, AlphaMAINDecoder,
    AlphaMDNMDecoder, AlphaMONMDecoder,
    AlphaMAOCDecoder, AlphaMAOFDecoder
)

__all__ = [
    # Registry
    'ChunkRegistry',
    'ChunkFormat',
    'chunk_registry',
    
    # Base
    'ChunkDecoder',
    'Vector3D',
    
    # Common chunks
    'MVERDecoder',
    'MTEXDecoder',
    'MPHDDecoder',
    'MAINDecoder',
    'MDDFDecoder',
    'MODFDecoder',
    'MMDXDecoder',
    'MMIDDecoder',
    'MWMODecoder',
    'MWIDDecoder',
    'MCNKDecoder',
    'MCVTDecoder',
    'MCNRDecoder',
    'MCLYDecoder',
    'MCALDecoder',
    'MCSHDecoder',
    'MCLQDecoder',
    'MCCVDecoder',
    
    # Alpha chunks
    'AlphaMPHDDecoder',
    'AlphaMAINDecoder',
    'AlphaMDNMDecoder',
    'AlphaMONMDecoder',
    'AlphaMAOCDecoder',
    'AlphaMAOFDecoder'
]