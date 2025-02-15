"""MCLQ (Legacy Water Data) chunk parser.

Contains legacy water information (pre-WotLK).
Only present in older ADT files or when converted from newer formats.

Structure:
1. Header (8 bytes):
   - First vertex index (uint16)
   - Vertex count (uint16)
   - Face count (uint16)
   - Flags (uint16)

2. Vertex array:
   - Array of 3D coordinates (float32 x 3)
   - Each vertex is 12 bytes

3. Face array:
   - Array of triangle indices (uint32 x 3)
   - Each face is 12 bytes
"""
from .parser import MclqChunk
from .header import MclqHeader

__all__ = ['MclqChunk', 'MclqHeader']