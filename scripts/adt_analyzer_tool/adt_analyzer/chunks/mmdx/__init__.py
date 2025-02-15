"""MMDX (M2 Model Filenames) chunk parser.

Contains a list of M2 model filenames used in the ADT file.
This chunk works in conjunction with MMID and MDDF chunks:

1. MMDX: Contains the actual model filenames as null-terminated strings
2. MMID: Contains offsets into MMDX data for each filename
3. MDDF: References models by their index in MMID

Example flow:
1. MDDF entry contains MMID index
2. MMID entry contains offset into MMDX
3. MMDX data at offset contains model filename

This system allows for efficient storage of repeated model
references while maintaining the full path information.
"""
from .parser import MmdxChunk

__all__ = ['MmdxChunk']