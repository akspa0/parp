"""
Base class for WDT (World Definition Table) file parsing.
Provides common functionality for both Alpha and Retail WDT formats.
"""
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging
import struct
from abc import abstractmethod

from .chunk_parser import ChunkParser, ChunkHeader

@dataclass
class MapTile:
    """Represents a map tile entry"""
    x: int
    y: int
    offset: int
    size: int
    flags: int
    async_id: int
    has_adt: bool = False

@dataclass
class ModelPlacement:
    """Represents a model (M2/WMO) placement"""
    name_id: int
    unique_id: int
    position: Tuple[float, float, float]
    rotation: Tuple[float, float, float]
    scale: float
    flags: int

class WDTParser(ChunkParser):
    """Base class for WDT parsing"""
    
    def __init__(self):
        """Initialize the WDT parser"""
        super().__init__()
        self.version: Optional[int] = None
        self.flags: Optional[int] = None
        self.tiles: Dict[Tuple[int, int], MapTile] = {}
        self.m2_models: List[str] = []
        self.wmo_models: List[str] = []
        self.m2_placements: List[ModelPlacement] = []
        self.wmo_placements: List[ModelPlacement] = []
    
    def _setup_chunk_registry(self) -> None:
        """Register common chunk parsers"""
        self.chunk_registry.update({
            'MVER': self._parse_mver,
            'MPHD': self._parse_mphd,
            'MAIN': self._parse_main,
        })
    
    def _parse_mver(self, data: bytes) -> Dict[str, Any]:
        """Parse MVER (Version) chunk"""
        self.version = struct.unpack('<I', data[:4])[0]
        return {'version': self.version}
    
    def _parse_mphd(self, data: bytes) -> Dict[str, Any]:
        """Parse MPHD (Map Header) chunk"""
        self.flags = struct.unpack('<I', data[:4])[0]
        flags_decoded = {
            'wdt_has_mwmo': bool(self.flags & 0x1),
            'use_global_map_obj': bool(self.flags & 0x2),
            'has_doodad_refs': bool(self.flags & 0x8),
            'has_terrain': bool(self.flags & 0x10),
            'has_normal_maps': bool(self.flags & 0x20),
            'has_vertex_colors': bool(self.flags & 0x40),
            'has_height_texturing': bool(self.flags & 0x80),
            'has_water_layers': bool(self.flags & 0x100)
        }
        return {
            'flags': self.flags,
            'decoded_flags': flags_decoded
        }
    
    def _parse_main(self, data: bytes) -> Dict[str, Any]:
        """Parse MAIN (Map Tile Table) chunk"""
        if len(data) != 64 * 64 * 16:  # 4096 entries * 16 bytes each
            raise ValueError(f"Invalid MAIN chunk size: {len(data)}")
        
        entries = []
        for y in range(64):
            for x in range(64):
                i = (y * 64 + x) * 16
                entry_data = data[i:i + 16]
                offset, size, flags, async_id = struct.unpack('<4I', entry_data)
                
                if flags & 0x1:  # has_adt flag
                    tile = MapTile(
                        x=x,
                        y=y,
                        offset=offset,
                        size=size,
                        flags=flags,
                        async_id=async_id,
                        has_adt=True
                    )
                    self.tiles[(x, y)] = tile
                    entries.append({
                        'coordinates': {'x': x, 'y': y},
                        'offset': offset,
                        'size': size,
                        'flags': flags,
                        'async_id': async_id
                    })
        
        return {'entries': entries}
    
    def get_tile(self, x: int, y: int) -> Optional[MapTile]:
        """Get tile at specified coordinates"""
        return self.tiles.get((x, y))
    
    def get_active_tiles(self) -> List[MapTile]:
        """Get list of all active (has_adt=True) tiles"""
        return list(self.tiles.values())
    
    def get_model_placement_grid(self) -> List[List[int]]:
        """
        Generate a 64x64 grid showing model placement density
        Returns a 2D list where each cell contains the number of models in that tile
        """
        grid = [[0] * 64 for _ in range(64)]
        
        # Helper to get tile coordinates from world position
        def get_tile_coords(x: float, y: float) -> Tuple[int, int]:
            return (int(x / 533.33333), int(y / 533.33333))
        
        # Count M2 placements
        for placement in self.m2_placements:
            x, y = get_tile_coords(placement.position[0], placement.position[1])
            if 0 <= x < 64 and 0 <= y < 64:
                grid[y][x] += 1
        
        # Count WMO placements
        for placement in self.wmo_placements:
            x, y = get_tile_coords(placement.position[0], placement.position[1])
            if 0 <= x < 64 and 0 <= y < 64:
                grid[y][x] += 1
        
        return grid
    
    @abstractmethod
    def parse(self) -> Dict[str, Any]:
        """
        Parse the WDT file
        Must be implemented by format-specific classes
        
        Returns:
            Dictionary containing parsed WDT data
        """
        pass
    
    @abstractmethod
    def parse_adt(self, tile: MapTile) -> Dict[str, Any]:
        """
        Parse ADT file for a given tile
        Must be implemented by format-specific classes
        
        Args:
            tile: MapTile object containing tile information
            
        Returns:
            Dictionary containing parsed ADT data
        """
        pass