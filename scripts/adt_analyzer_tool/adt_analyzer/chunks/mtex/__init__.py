"""MTEX (Texture Names) chunk parser.

Contains a list of texture filenames used in the terrain.
This chunk works in conjunction with MCLY and MCAL chunks:

1. MTEX: Contains texture filenames as null-terminated strings
2. MCLY: References textures by their index in MTEX array
3. MCAL: Contains alpha maps for blending textures

Texture System:
- Each MCNK (map chunk) can have multiple texture layers
- MCLY entries reference MTEX indices for their textures
- MCAL provides alpha maps for blending between layers
- Layers are rendered from bottom to top with alpha blending

Example:
If MCLY entry has texture_id = 3, it uses the fourth texture
name from the MTEX array (zero-based indexing). The alpha map
in MCAL determines how this texture blends with other layers.
"""
from .parser import MtexChunk

__all__ = ['MtexChunk']