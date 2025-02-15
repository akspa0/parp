"""MCNR (Normal Map) chunk parser.

Contains normal vectors for terrain vertices.
Each normal is 3 signed bytes representing normalized vector components.
"""
from .parser import McnrChunk

__all__ = ['McnrChunk']