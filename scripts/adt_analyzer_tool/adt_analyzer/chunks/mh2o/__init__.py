"""MH2O (Water Data) chunk parser.

Contains water information for terrain chunks.
This is the modern water system that replaced MCLQ.

Structure:
1. Layer Headers (128 bytes total):
   - Up to 8 layers per chunk
   - Each header is 16 bytes
   - Contains flags, dimensions, and offsets

2. Layer Data:
   Each layer can have:
   - Base height level
   - Optional vertex height grid
   - Optional render flags grid
   
Properties:
- Multiple layers allow for waterfalls and overlapping water
- Vertex heights enable waves and varying water levels
- Render flags control visual effects
- Flags for gameplay mechanics (fishable, fatigue)

Relationships:
- Replaced MCLQ (Legacy Water) chunk
- Referenced by MHDR chunk
- Part of modern water rendering system
"""
from .parser import Mh2oChunk
from .header import Mh2oLayerHeader
from .layer import Mh2oLayer

__all__ = ['Mh2oChunk', 'Mh2oLayerHeader', 'Mh2oLayer']