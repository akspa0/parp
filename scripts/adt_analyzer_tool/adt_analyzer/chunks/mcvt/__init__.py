"""MCVT (Height Map) chunk parser.

Contains height information for the terrain.
9x9 + 8x8 = 145 vertices total.
"""
from .parser import McvtChunk

__all__ = ['McvtChunk']