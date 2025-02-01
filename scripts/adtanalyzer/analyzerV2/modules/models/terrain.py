"""
Core terrain data structures for WoW terrain files.
Uses dataclasses for clean, type-safe implementations.
"""
from dataclasses import dataclass, field
from enum import Flag, auto
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

@dataclass
class Vector3D:
    """3D vector with x, y, z coordinates"""
    x: float
    y: float
    z: float

@dataclass
class RGBA:
    """RGBA color value"""
    r: int
    g: int
    b: int
    a: int

@dataclass
class CAaBox:
    """Axis-aligned bounding box"""
    min: Vector3D
    max: Vector3D

class MCNKFlags(Flag):
    """MCNK chunk flags"""
    HAS_SHADOWS = auto()
    IMPASS = auto()
    LQ_RIVER = auto()
    LQ_OCEAN = auto()
    LQ_MAGMA = auto()
    LQ_SLIME = auto()
    HAS_VERTEX_COLORS = auto()
    HAS_2_OR_MORE_LAYERS = auto()
    HAS_BIG_ALPHA = auto()
    DO_NOT_FIX_ALPHA_MAP = auto()
    HAS_HEIGHT_TEXTURE = auto()
    HAS_HEIGHT_ALPHA = auto()
    USE_COMPRESSED_HEIGHT = auto()
    USE_OFFSET_HEIGHT = auto()
    USE_COMPRESSED_OFFSET = auto()
    HAS_TANGENTS = auto()
    HAS_VERTICES = auto()
    FULL_WATER = auto()

class WDTFlags(Flag):
    """WDT file flags"""
    GLOBAL_WMO = auto()
    HAS_MPHD = auto()
    HAS_MAIN = auto()
    HAS_MAID = auto()
    HAS_MODF = auto()
    HAS_TEXTURE_FLAGS = auto()

@dataclass
class TextureInfo:
    """Texture information"""
    filename: str
    flags: int = 0
    effect_id: int = 0
    layer_index: int = 0
    blend_mode: int = 0
    is_compressed: bool = False

@dataclass
class TextureLayer:
    """Texture layer with alpha map"""
    texture_id: int
    flags: int
    effect_id: Optional[int] = None
    layer_index: int = 0
    blend_mode: int = 0
    is_compressed: bool = False
    alpha_map: Optional[List[int]] = None

@dataclass
class ModelReference:
    """Reference to an M2 or WMO model"""
    path: str
    format_type: str = 'retail'

@dataclass
class ModelPlacement:
    """Base model placement data"""
    name_id: int
    unique_id: int
    position: Vector3D
    rotation: Vector3D
    scale: float
    flags: int

@dataclass
class WMOPlacement(ModelPlacement):
    """WMO model placement with additional data"""
    doodad_set: int = 0
    name_set: int = 0
    bounding_box: Optional[CAaBox] = None

@dataclass
class MapTile:
    """Map tile information from WDT"""
    x: int
    y: int
    offset: int = 0
    size: int = 0
    flags: int = 0
    async_id: int = 0

@dataclass
class MCNKInfo:
    """MCNK chunk information"""
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
    texture_layers: List[TextureLayer] = field(default_factory=list)
    height_map: Optional[List[float]] = None
    normal_data: Optional[List[float]] = None
    liquid_heights: Optional[List[float]] = None
    liquid_flags: Optional[List[int]] = None

@dataclass
class TerrainFile:
    """Base class for terrain files"""
    path: Union[str, Path]
    file_type: str  # 'adt' or 'wdt'
    format_type: str  # 'alpha' or 'retail'
    version: int
    flags: Union[MCNKFlags, WDTFlags]
    map_name: str
    chunk_order: List[str]

@dataclass
class ADTFile(TerrainFile):
    """ADT terrain file data"""
    textures: List[TextureInfo] = field(default_factory=list)
    m2_models: List[str] = field(default_factory=list)
    wmo_models: List[str] = field(default_factory=list)
    m2_placements: List[ModelPlacement] = field(default_factory=list)
    wmo_placements: List[WMOPlacement] = field(default_factory=list)
    mcnk_chunks: Dict[Tuple[int, int], MCNKInfo] = field(default_factory=dict)
    subchunks: Dict[Tuple[int, int], Dict[str, Dict]] = field(default_factory=dict)

@dataclass
class WDTFile(TerrainFile):
    """WDT terrain file data"""
    tiles: Dict[Tuple[int, int], MapTile] = field(default_factory=dict)
    m2_models: List[ModelReference] = field(default_factory=list)
    wmo_models: List[ModelReference] = field(default_factory=list)
    m2_placements: List[ModelPlacement] = field(default_factory=list)
    wmo_placements: List[WMOPlacement] = field(default_factory=list)
    is_global_wmo: bool = False