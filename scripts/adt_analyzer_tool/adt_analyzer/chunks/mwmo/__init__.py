"""MWMO (WMO Filenames) chunk parser.

Contains a list of WMO (World Model Object) filenames used in the ADT file.
This chunk works in conjunction with MWID and MODF chunks:

1. MWMO: Contains the actual WMO filenames as null-terminated strings
2. MWID: Contains offsets into MWMO data for each filename
3. MODF: References WMOs by their index in MWID

Example flow:
1. MODF entry contains MWID index
2. MWID entry contains offset into MWMO
3. MWMO data at offset contains WMO filename

This system parallels the M2 model system (MMDX/MMID/MDDF)
but is specifically for WMO files, which typically represent
larger world objects like buildings and terrain features.
"""
from .parser import MwmoChunk

__all__ = ['MwmoChunk']