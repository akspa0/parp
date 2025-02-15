"""MCAL (Alpha Map) chunk parser.

Contains alpha maps used for texture layer blending.
This chunk works in conjunction with the MCLY chunk:

1. MCLY entries contain:
   - Offset into this chunk's data for their alpha map
   - Flags that determine how the alpha map data should be interpreted

2. The alpha map data in this chunk is referenced by MCLY entries
   and used to control texture blending between layers.
"""
from .parser import McalChunk

__all__ = ['McalChunk']