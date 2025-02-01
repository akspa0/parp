"""
Chunk data models for ADT file parsing.
Based on WoWDev wiki specifications: https://wowdev.wiki/ADT/v18
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Union
from enum import IntFlag, auto

from ..utils.common_types import Vector2D, Vector3D, Quaternion, CAaBox, RGB, RGBA

class MCNKFlags(IntFlag):
    """Flags used in MCNK chunks"""
    HasMCVT = auto()  # Has vertex height data
    HasMCNR = auto()  # Has normal data
    HasMCLY = auto()  # Has texture layer data
    HasMCRF = auto()  # Has doodad references
    HasMCAL = auto()  # Has alpha maps
    HasMCSH = auto()  # Has shadow map
    HasMCSE = auto()  # Has sound emitters
    HasMCLQ = auto()  # Has liquid data
    HasMCCV = auto()  # Has vertex colors

@dataclass
class ChunkHeader:
    """Common chunk header structure"""
    magic: bytes  # 4-byte chunk identifier
    size: int    # Size of chunk data (excluding header)

@dataclass
class TextureInfo:
    """Texture information from MTEX chunk"""
    filename: str
    flags: int = 0
    effect_id: Optional[int] = None

@dataclass
class ModelPlacement:
    """Base class for model placement data (MDDF/MODF)"""
    name_id: int
    unique_id: int
    position: Vector3D
    rotation: Vector3D  # Euler angles in radians
    scale: float
    flags: int

    @property
    def rotation_quaternion(self) -> Quaternion:
        """Get rotation as quaternion"""
        return Quaternion.from_euler(self.rotation.x, self.rotation.y, self.rotation.z)

@dataclass
class WMOPlacement(ModelPlacement):
    """Additional WMO placement data"""
    doodad_set: int
    name_set: int
    bounding_box: CAaBox

@dataclass
class MCNKInfo:
    """MCNK chunk header information"""
    flags: MCNKFlags
    index_x: int
    index_y: int
    n_layers: int
    n_doodad_refs: int
    position: Vector3D
    area_id: int
    holes: int
    layer_flags: int
    render_flags: int
    has_layer_height: bool
    min_elevation: float
    max_elevation: float
    liquid_type: int
    predTex: int
    noEffectDoodad: int
    holes_high_res: int

@dataclass
class MCVTData:
    """Height map data from MCVT chunk"""
    heights: List[float]  # 145 vertices per chunk (9x17 grid)

@dataclass
class MCNRData:
    """Normal data from MCNR chunk"""
    normals: List[Vector3D]  # 145 normals

@dataclass
class MCLYEntry:
    """Single texture layer info from MCLY chunk"""
    texture_id: int
    flags: int
    offset_mcal: int
    effect_id: int
    layer_height: Optional[float] = None

@dataclass
class MCALData:
    """Alpha map data from MCAL chunk"""
    alpha_map: bytes
    compressed: bool

@dataclass
class MCLQData:
    """Liquid data from MCLQ chunk"""
    heights: List[float]
    flags: List[int]
    data: bytes  # Raw liquid data for version-specific parsing

@dataclass
class MCCVData:
    """Vertex color data from MCCV chunk"""
    colors: List[RGBA]  # RGBA colors for vertices

@dataclass
class ADTFile:
    """Complete ADT file structure"""
    version: int
    textures: List[TextureInfo]
    m2_models: List[str]
    wmo_models: List[str]
    m2_placements: List[ModelPlacement]
    wmo_placements: List[WMOPlacement]
    mcnk_chunks: Dict[tuple[int, int], MCNKInfo]  # Keyed by (x,y) coordinates
    subchunks: Dict[tuple[int, int], Dict[str, Union[MCVTData, MCNRData, List[MCLYEntry], MCALData, MCLQData, MCCVData]]]