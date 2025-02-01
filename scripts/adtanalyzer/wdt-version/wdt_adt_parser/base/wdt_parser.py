"""
Base class for WDT (World Definition Table) file parsing.
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging
import struct
from abc import ABC, abstractmethod
from enum import Enum, auto

from .chunk_parser import ChunkParser, ChunkHeader
from ..database import DatabaseManager
from .visualization import create_visualizer

class ParsingPhase(Enum):
    """Parsing phases for WDT analysis"""
    FILE_STRUCTURE = auto()  # Analyze file format and structure
    CHUNK_PROCESSING = auto()  # Process individual chunks
    MAP_STRUCTURE = auto()  # Process map tiles and structure
    ASSET_PROCESSING = auto()  # Process models and textures

@dataclass
class MapTile:
    """Map tile information"""
    x: int
    y: int
    offset: int
    size: int
    flags: int
    async_id: int
    has_adt: bool

@dataclass
class ModelPlacement:
    """Model placement information"""
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
        # Core data
        self.version: Optional[int] = None
        self.flags: Optional[int] = None
        self.tiles: Dict[Tuple[int, int], MapTile] = {}
        self.m2_models: List[str] = []
        self.wmo_models: List[str] = []
        self.m2_placements: List[ModelPlacement] = []
        self.wmo_placements: List[ModelPlacement] = []
        
        # Database connection
        self.db: Optional[DatabaseManager] = None
        self.wdt_id: Optional[int] = None
        
        # Parsing state
        self.chunk_order: List[str] = []
        self.active_tiles = 0
        self.current_phase: ParsingPhase = ParsingPhase.FILE_STRUCTURE
        
        # Visualization
        self.grid = [[0] * 64 for _ in range(64)]  # Map grid for visualization
        self.visualizer = create_visualizer()
        
        # Phase results
        self.phase_results: Dict[ParsingPhase, Dict[str, Any]] = {
            phase: {} for phase in ParsingPhase
        }
    
    def _setup_chunk_registry(self) -> None:
        """Register common chunk parsers"""
        self.chunk_registry.update({
            'MVER': self._parse_mver,  # Version info
            'MPHD': self._parse_mphd,  # Map header
        })
    
    def _parse_mver(self, data: bytes) -> Dict[str, Any]:
        """Parse MVER (Version) chunk"""
        if len(data) < 4:
            raise ValueError(f"Invalid MVER chunk size: {len(data)}")
        
        self.version = struct.unpack('<I', data[:4])[0]
        return {'version': self.version}
    
    def _parse_mphd(self, data: bytes) -> Dict[str, Any]:
        """
        Parse MPHD (Map Header) chunk
        Must be implemented by format-specific classes
        """
        raise NotImplementedError("MPHD parsing must be implemented by format-specific classes")
    
    def get_tile(self, x: int, y: int) -> Optional[MapTile]:
        """Get tile at specified coordinates"""
        return self.tiles.get((x, y))
    
    def get_active_tiles(self) -> List[MapTile]:
        """Get list of active tiles"""
        return list(self.tiles.values())
    
    def get_model_names(self) -> Tuple[List[str], List[str]]:
        """Get lists of M2 and WMO model names"""
        return self.m2_models, self.wmo_models
    
    def get_model_placements(self) -> Tuple[List[ModelPlacement], List[ModelPlacement]]:
        """Get lists of M2 and WMO model placements"""
        return self.m2_placements, self.wmo_placements
    
    def set_database(self, db: DatabaseManager, wdt_id: int):
        """Set database connection and WDT ID"""
        self.db = db
        self.wdt_id = wdt_id
    
    def store_chunk_offset(self, header: ChunkHeader):
        """Store chunk offset in database"""
        if self.db and self.wdt_id:
            self.db.insert_chunk_offset(
                self.wdt_id,
                header.name,
                header.offset,
                header.size,
                header.data_offset
            )
    
    def store_tile(self, x: int, y: int, tile: MapTile):
        """Store tile information in database"""
        if self.db and self.wdt_id:
            self.db.insert_map_tile(
                self.wdt_id,
                x, y,
                tile.offset,
                tile.size,
                tile.flags,
                tile.async_id
            )
    
    def store_model(self, name: str, is_m2: bool, x: int = -1, y: int = -1):
        """Store model information in database"""
        if self.db and self.wdt_id:
            if is_m2:
                self.db.insert_m2_model(
                    self.wdt_id,
                    x, y,
                    name,
                    'alpha' if hasattr(self, 'is_alpha') and self.is_alpha else 'retail'
                )
            else:
                self.db.insert_wmo_model(
                    self.wdt_id,
                    x, y,
                    name,
                    'alpha' if hasattr(self, 'is_alpha') and self.is_alpha else 'retail'
                )
    
    def generate_visualizations(self, output_dir: Optional[Path] = None) -> Dict[str, Path]:
        """
        Generate visualizations of the map grid
        
        Args:
            output_dir: Optional output directory for visualization files
            
        Returns:
            Dictionary containing paths to generated visualization files
        """
        try:
            vis_files = {}
            
            # Generate text visualization
            text_file = self.visualizer.write_visualization(
                self.grid,
                output_dir=output_dir,
                prefix="adt_visualization"
            )
            vis_files['text'] = text_file
            
            # Generate HTML visualization
            html_file = self.visualizer.write_html_visualization(
                self.grid,
                output_dir=output_dir,
                prefix="adt_visualization"
            )
            vis_files['html'] = html_file
            
            return vis_files
            
        except Exception as e:
            self.logger.error(f"Failed to generate visualizations: {e}")
            raise
    
    def process_phase(self, phase: ParsingPhase) -> Dict[str, Any]:
        """
        Process a specific parsing phase
        
        Args:
            phase: The parsing phase to process
            
        Returns:
            Dictionary containing phase results
        """
        self.current_phase = phase
        self.logger.info(f"\nPhase: {phase.name}")
        
        try:
            if phase == ParsingPhase.FILE_STRUCTURE:
                # Analyze format and basic structure
                results = self._process_file_structure()
            elif phase == ParsingPhase.CHUNK_PROCESSING:
                # Process and store individual chunks
                results = self._process_chunks()
            elif phase == ParsingPhase.MAP_STRUCTURE:
                # Process map tiles and structure
                results = self._process_map_structure()
            elif phase == ParsingPhase.ASSET_PROCESSING:
                # Process models and textures
                results = self._process_assets()
            else:
                raise ValueError(f"Unknown parsing phase: {phase}")
                
            self.phase_results[phase] = results
            return results
            
        except Exception as e:
            self.logger.error(f"Error in {phase.name} phase: {e}")
            self.phase_results[phase] = {'error': str(e)}
            raise
    
    def _process_file_structure(self) -> Dict[str, Any]:
        """Process file structure phase - must be implemented by subclasses"""
        raise NotImplementedError
        
    def _process_chunks(self) -> Dict[str, Any]:
        """Process chunks phase - must be implemented by subclasses"""
        raise NotImplementedError
        
    def _process_map_structure(self) -> Dict[str, Any]:
        """Process map structure phase - must be implemented by subclasses"""
        raise NotImplementedError
        
    def _process_assets(self) -> Dict[str, Any]:
        """Process assets phase - must be implemented by subclasses"""
        raise NotImplementedError
    
    @abstractmethod
    def parse(self) -> Dict[str, Any]:
        """
        Parse the WDT file
        Must be implemented by format-specific classes
        
        Returns:
            Dictionary containing parsed WDT data
        """
        pass