"""
Data models for WoW Terrain Analyzer.
Provides type-safe data structures using dataclasses.
"""

from .terrain import (
    # Base structures
    Vector3D,
    RGBA,
    CAaBox,
    
    # Flags
    MCNKFlags,
    WDTFlags,
    
    # Texture related
    TextureInfo,
    TextureLayer,
    
    # Model related
    ModelReference,
    ModelPlacement,
    WMOPlacement,
    
    # Map related
    MapTile,
    MCNKInfo,
    
    # File types
    TerrainFile,
    ADTFile,
    WDTFile,
)

__all__ = [
    # Base structures
    'Vector3D',
    'RGBA',
    'CAaBox',
    
    # Flags
    'MCNKFlags',
    'WDTFlags',
    
    # Texture related
    'TextureInfo',
    'TextureLayer',
    
    # Model related
    'ModelReference',
    'ModelPlacement',
    'WMOPlacement',
    
    # Map related
    'MapTile',
    'MCNKInfo',
    
    # File types
    'TerrainFile',
    'ADTFile',
    'WDTFile',
]

# Type aliases
from typing import Dict, List, Optional, Set, Tuple, Union
from pathlib import Path

TerrainDict = Dict[str, any]
ModelDict = Dict[str, any]
TextureDict = Dict[str, any]
ChunkDict = Dict[Tuple[int, int], Dict[str, any]]

__all__ += [
    'TerrainDict',
    'ModelDict',
    'TextureDict',
    'ChunkDict',
]