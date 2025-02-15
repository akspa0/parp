"""MODF (WMO Placement) chunk parser.

Contains placement information for WMO (World Model Object) instances.
This chunk works in conjunction with MWMO and MWID chunks:

1. MWMO: Contains WMO filenames as null-terminated strings
2. MWID: Contains offsets into MWMO data
3. MODF: Contains placement data for WMO instances

Each MODF entry contains:
- MWID index: References the WMO model through MWID->MWMO
- Position: XYZ coordinates in world space
- Rotation: XYZ rotation angles
- Scale: Model scale factor (if applicable)
- Flags: Various rendering and behavior flags

This system parallels the M2 model system (MDDF/MMID/MMDX)
but is specifically for larger world objects like buildings
and terrain features.
"""
from .parser import ModfChunk
from .entry import ModfEntry

__all__ = ['ModfChunk', 'ModfEntry']