"""
Base class for ADT (Area Definition Table) file parsing.
"""
from typing import Dict, Any, Optional, Union, List, Tuple
from pathlib import Path
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from .chunk_parser import ChunkParser

@dataclass
class HeightmapInfo:
    """Heightmap information"""
    heights: List[float]
    min_height: float
    max_height: float

@dataclass
class LayerInfo:
    """Texture layer information"""
    texture_id: int
    flags: int
    effect_id: int
    blend_mode: int

@dataclass
class LiquidInfo:
    """Liquid information"""
    type: int
    heights: List[float]
    flags: int

@dataclass
class MCNKInfo:
    """MCNK chunk information"""
    flags: int
    area_id: int
    n_layers: int
    n_doodad_refs: int
    holes: int
    heightmap: Optional[HeightmapInfo] = None
    layers: Optional[List[LayerInfo]] = None
    liquid: Optional[LiquidInfo] = None
    offsets: Optional[Dict[str, int]] = None

class ADTParser(ChunkParser):
    """Base class for ADT parsing"""
    
    def __init__(self):
        """Initialize the ADT parser"""
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.x: int = -1  # Tile X coordinate
        self.y: int = -1  # Tile Y coordinate
        self.mcnk_chunks: List[MCNKInfo] = []
        self.textures: List[str] = []
        self.version: Optional[int] = None
    
    def _setup_chunk_registry(self) -> None:
        """Register common chunk parsers"""
        # Base ADT parsers - specific formats will add their own
        self.chunk_registry.update({
            'MVER': self._parse_mver,  # Version info
        })
    
    def _parse_mver(self, data: bytes) -> Dict[str, Any]:
        """Parse MVER (Version) chunk"""
        if len(data) < 4:
            raise ValueError(f"Invalid MVER chunk size: {len(data)}")
        
        version = int.from_bytes(data[:4], byteorder='little')
        self.version = version
        self.logger.info(f"ADT Version: {version}")
        
        return {'version': version}
    
    def get_mcnk_info(self, index: int) -> Optional[MCNKInfo]:
        """Get MCNK chunk information by index"""
        if 0 <= index < len(self.mcnk_chunks):
            return self.mcnk_chunks[index]
        return None
    
    def get_texture_name(self, index: int) -> Optional[str]:
        """Get texture name by index"""
        if 0 <= index < len(self.textures):
            return self.textures[index]
        return None
    
    def get_heightmap(self, mcnk_index: int) -> Optional[HeightmapInfo]:
        """Get heightmap for MCNK chunk"""
        mcnk = self.get_mcnk_info(mcnk_index)
        return mcnk.heightmap if mcnk else None
    
    def get_layers(self, mcnk_index: int) -> List[LayerInfo]:
        """Get texture layers for MCNK chunk"""
        mcnk = self.get_mcnk_info(mcnk_index)
        return mcnk.layers if mcnk and mcnk.layers else []
    
    def get_liquid(self, mcnk_index: int) -> Optional[LiquidInfo]:
        """Get liquid information for MCNK chunk"""
        mcnk = self.get_mcnk_info(mcnk_index)
        return mcnk.liquid if mcnk else None
    
    @abstractmethod
    def parse(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Parse ADT file
        
        Args:
            file_path: Path to ADT file
            
        Returns:
            Dictionary containing parsed ADT data
        """
        pass
    
    @abstractmethod
    def parse_embedded_data(self, data: bytes, x: int, y: int) -> Dict[str, Any]:
        """
        Parse embedded ADT data from WDT file
        
        Args:
            data: Raw ADT data from WDT file
            x: X coordinate of tile
            y: Y coordinate of tile
            
        Returns:
            Dictionary containing parsed ADT data
        """
        pass
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()