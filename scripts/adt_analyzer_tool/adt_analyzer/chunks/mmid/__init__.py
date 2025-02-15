"""MMID (M2 Model Indices) chunk parser.

Contains offsets into the MMDX chunk for model filenames.
This chunk works in conjunction with MMDX and MDDF chunks:

1. MMID: Array of uint32 offsets into MMDX data
2. MMDX: Contains the actual model filenames
3. MDDF: References models using indices into this chunk

Example flow:
1. MDDF entry contains index N
2. MMID[N] contains offset into MMDX
3. MMDX data at offset contains model filename

The MMID chunk serves as a lookup table, allowing MDDF entries
to reference model filenames indirectly through offsets into
the MMDX chunk's data. This system allows for efficient storage
and lookup of model references.
"""
from .parser import MmidChunk

__all__ = ['MmidChunk']