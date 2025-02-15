"""MCSH (Shadow Map) chunk parser.

Contains a shadow intensity map for the terrain chunk.

Structure:
- 64x64 grid of bytes
- Each byte represents shadow intensity for a cell:
  * 0 = No shadow
  * 255 = Full shadow
  * Values between represent partial shadow

Usage:
- Used for static shadows on the terrain
- Independent of dynamic shadows from objects/time of day
- May be incomplete in some ADT files (particularly older ones)
- Grid coordinates correspond to terrain subdivisions

Note:
The shadow map provides a base shadow layer that is combined
with dynamic shadows at runtime to create the final shadow
appearance in the game.
"""
from .parser import McshChunk

__all__ = ['McshChunk']