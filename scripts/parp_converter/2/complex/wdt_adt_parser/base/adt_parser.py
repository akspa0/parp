"""
Base class for ADT (Area Definition Table) file parsing.
Provides common functionality for both Alpha and Retail ADT formats.
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging
import struct
from abc import abstractmethod

from .chunk_parser import ChunkParser, ChunkHeader

@dataclass
class MCNKInfo:
    """Map chunk (MCNK) information"""
    index_x: int
    index_y: int
    flags: int
    area_id: int
    holes: int
    layer_count: int
    doodad_refs: int
    offset: int
    size: int

@dataclass
class LayerInfo:
    """Texture layer information"""
    texture_id: int
    flags: int
    effect_id: int
    blend_mode: int

@dataclass
class HeightmapInfo:
    """Heightmap information"""
    heights: List[float]
    holes: int

@dataclass
class LiquidInfo:
    """Liquid information"""
    type: int
    height_map: List[float]
    flags: int
    min_height: float
    max_height: float

class ADTParser(ChunkParser):
    """Base class for ADT parsing"""
    
    CHUNK_SIZE = 16  # ADT chunks are 16x16
    GRID_SIZE = 8    # 8x8 grid of chunks
    
    def __init__(self):
        """Initialize the ADT parser"""
        super().__init__()
        self.version: Optional[int] = None
        self.chunks: List[List[Optional[MCNKInfo]]] = [[None] * self.GRID_SIZE for _ in range(self.GRID_SIZE)]
        self.textures: List[str] = []
        self.models: List[str] = []
        self.wmos: List[str] = []
    
    def _setup_chunk_registry(self) -> None:
        """Register common chunk parsers"""
        self.chunk_registry.update({
            'MVER': self._parse_mver,
            'MHDR': self._parse_mhdr,
            'MCNK': self._parse_mcnk,
            'MTEX': self._parse_mtex
        })
    
    def _parse_mver(self, data: bytes) -> Dict[str, Any]:
        """Parse MVER (Version) chunk"""
        self.version = struct.unpack('<I', data[:4])[0]
        return {'version': self.version}
    
    def _parse_mhdr(self, data: bytes) -> Dict[str, Any]:
        """Parse MHDR (Map Header) chunk"""
        if len(data) < 64:
            raise ValueError(f"Invalid MHDR chunk size: {len(data)}")
            
        offsets = {}
        offset_names = ['mcin', 'mtex', 'mmdx', 'mmid', 'mwmo', 'mwid', 'mddf', 'modf']
        
        for i, name in enumerate(offset_names):
            offset = struct.unpack('<I', data[i*4:(i+1)*4])[0]
            if offset > 0:
                offsets[name] = offset
        
        return {'offsets': offsets}
    
    def _parse_mcnk(self, data: bytes) -> Dict[str, Any]:
        """
        Parse MCNK (Map Chunk) chunk header
        Format-specific implementations should override this for full parsing
        """
        if len(data) < 128:  # Minimum header size
            raise ValueError(f"Invalid MCNK chunk size: {len(data)}")
            
        # Parse common header fields
        flags = struct.unpack('<I', data[0:4])[0]
        idx_x = struct.unpack('<I', data[4:8])[0]
        idx_y = struct.unpack('<I', data[8:12])[0]
        layer_count = struct.unpack('<I', data[12:16])[0]
        doodad_refs = struct.unpack('<I', data[16:20])[0]
        
        return {
            'flags': flags,
            'position': {'x': idx_x, 'y': idx_y},
            'layer_count': layer_count,
            'doodad_refs': doodad_refs
        }
    
    def _parse_mtex(self, data: bytes) -> Dict[str, Any]:
        """Parse MTEX (Map Textures) chunk"""
        textures = data.split(b'\0')
        self.textures = [tex.decode('utf-8', 'ignore') for tex in textures if tex]
        return {'textures': self.textures}
    
    def get_chunk(self, x: int, y: int) -> Optional[MCNKInfo]:
        """Get chunk at specified coordinates"""
        if 0 <= x < self.GRID_SIZE and 0 <= y < self.GRID_SIZE:
            return self.chunks[y][x]
        return None
    
    def get_heightmap(self, chunk_x: int, chunk_y: int) -> Optional[HeightmapInfo]:
        """
        Get heightmap data for a specific chunk
        Must be implemented by format-specific classes
        """
        return None
    
    def get_texture_layers(self, chunk_x: int, chunk_y: int) -> List[LayerInfo]:
        """
        Get texture layers for a specific chunk
        Must be implemented by format-specific classes
        """
        return []
    
    def get_liquid_data(self, chunk_x: int, chunk_y: int) -> Optional[LiquidInfo]:
        """
        Get liquid data for a specific chunk
        Must be implemented by format-specific classes
        """
        return None
    
    @abstractmethod
    def parse(self) -> Dict[str, Any]:
        """
        Parse the ADT file
        Must be implemented by format-specific classes
        
        Returns:
            Dictionary containing parsed ADT data
        """
        pass