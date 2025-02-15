"""MWID (WMO Indices) chunk parser.

Contains offsets into the MWMO chunk for WMO filenames.
This chunk works in conjunction with MWMO and MODF chunks:

1. MWID: Array of uint32 offsets into MWMO data
2. MWMO: Contains the actual WMO filenames
3. MODF: References WMOs using indices into this chunk

Example flow:
1. MODF entry contains index N
2. MWID[N] contains offset into MWMO
3. MWMO data at offset contains WMO filename

The MWID chunk serves as a lookup table, allowing MODF entries
to reference WMO filenames indirectly through offsets into
the MWMO chunk's data. This system parallels the M2 model
system (MMID/MMDX/MDDF) but is specifically for WMO files.
"""
from .parser import MwidChunk

__all__ = ['MwidChunk']