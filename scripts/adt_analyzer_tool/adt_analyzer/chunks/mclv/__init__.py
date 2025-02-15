"""MCLV (Light Values) chunk parser.

Contains light information for terrain vertices.
This chunk is part of the legacy lighting system.

Format:
- Each entry is a 32-bit color value
- Number of entries varies based on chunk size
- Unlike MCCV/MCVT, not fixed to vertex count

Legacy Usage:
- Used in older versions for terrain lighting
- May be present in converted files
- Modern ADT files typically use other lighting methods
"""
from .parser import MclvChunk

__all__ = ['MclvChunk']