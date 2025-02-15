"""MCCV (Vertex Colors) chunk parser.

Contains vertex colors for terrain vertices.
This chunk corresponds directly to MCVT vertices:
- Same number of entries (145 = 9*9 + 8*8)
- Same vertex ordering

Color Format:
- Stored as BGRA in file (4 bytes per color)
- Converted to RGBA when parsed
- Each component is 0-255 (unsigned byte)

Usage:
- These colors can be used to tint the terrain
- Often used for additional detail or blending
"""
from .parser import MccvChunk

__all__ = ['MccvChunk']