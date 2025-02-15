"""MCLY (Texture Layer) chunk parser.

Contains information about texture layers in the terrain.
Each layer entry specifies texture properties and alpha map location.
"""
from .parser import MclyChunk
from .entry import MclyEntry

__all__ = ['MclyChunk', 'MclyEntry']