"""MCRF (Doodad References) chunk parser.

Contains references to M2/WMO model placements in this map chunk.
This chunk works in conjunction with MDDF and MODF chunks:

1. MDDF chunk: Contains M2 model placement information
2. MODF chunk: Contains WMO model placement information
3. MCRF chunk: References entries from both MDDF and MODF

The indices in this chunk refer to the combined set of placements
from both MDDF and MODF chunks, allowing each map chunk to reference
specific model placements that affect its area.
"""
from .parser import McrfChunk

__all__ = ['McrfChunk']