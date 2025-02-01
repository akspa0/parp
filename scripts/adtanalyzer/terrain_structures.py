"""
Common data structures for WoW terrain file parsing.
Supports both ADT and WDT formats, including Alpha and Retail versions.
"""
import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Union
from enum import IntFlag, auto

@dataclass
class Vector3D:
    """3D vector"""
    x: float
    y: float
    z: float
    
    @classmethod
    def unpack(cls, data: bytes, offset: int = 0) -> 'Vector3D':
        """Unpack from binary data"""
        x, y, z = struct.unpack('<3f', data[offset:offset+12])
        return cls(x, y, z)

@dataclass
class Quaternion:
    """Quaternion (x, y, z, w)"""
    x: float
    y: float
    z: float
    w: float
    
    @classmethod
    def from_euler(cls, x: float, y: float, z: float) -> 'Quaternion':
        """Create from Euler angles (radians)"""
        import math
        cx = math.cos(x * 0.5)
        sx = math.sin(x * 0.5)
        cy = math.cos(y * 0.5)
        sy = math.sin(y * 0.5)
        cz = math.cos(z * 0.5)
        sz = math.sin(z * 0.5)
        
        return cls(
            x=sx * cy * cz - cx * sy * sz,
            y=cx * sy * cz + sx * cy * sz,
            z=cx * cy * sz - sx * sy * cz,
            w=cx * cy * cz + sx * sy * sz
        )

@dataclass
class RGBA:
    """RGBA color"""
    r: int
    g: int
    b: int
    a: int

@dataclass
class CAaBox:
    """Axis-aligned bounding box"""
    min: Vector3D
    max: Vector3D

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

class WDTFlags(IntFlag):
    """WDT header flags"""
    GlobalWMO = auto()      # Map is a global WMO
    HasADTFiles = auto()    # Map uses ADT files
    HasMCCV = auto()        # Has vertex colors
    HasMCLV = auto()        # Has vertex lighting
    HasMCAL = auto()        # Has alpha maps
    HasMCSH = auto()        # Has shadows
    HasMCSE = auto()        # Has sound emitters
    HasMCLQ = auto()        # Has liquid data

@dataclass
class TextureLayer:
    """
    Texture layer information from MCLY chunk
    
    Flags:
    - 0x001: Animation enabled
    - 0x002: Animation speed multiplier
    - 0x004: Animation rotation multiplier
    - 0x008: Animation wave multiplier
    - 0x010: Alpha map is compressed
    - 0x020: Ground effect
    - 0x040: Do not compress alpha map
    - 0xFF000000: Alpha map blend mode
    """
    texture_id: int  # Index into file's MTEX list
    flags: int  # Alpha map and animation flags
    offset_mcal: int  # Offset into MCAL data
    effect_id: Optional[int]  # Index into ADT's MCRF chunk, None if no effect
    layer_index: int  # Order in layer stack
    blend_mode: int  # Alpha map blend mode
    is_compressed: bool = False  # Whether alpha map is compressed
    alpha_map: Optional[List[int]] = None  # Alpha values from MCAL (64x64 = 4096 bytes)

@dataclass
class TextureInfo:
    """Texture information"""
    filename: str
    flags: int = 0
    effect_id: Optional[int] = None
    layer_index: Optional[int] = None
    blend_mode: Optional[int] = None
    is_compressed: bool = False
    alpha_map: Optional[List[int]] = None

@dataclass
class ModelPlacement:
    """Base class for model placement data"""
    name_id: int
    unique_id: int
    position: Vector3D
    rotation: Vector3D
    scale: float
    flags: int

@dataclass
class WMOPlacement(ModelPlacement):
    """Additional WMO placement data"""
    doodad_set: int
    name_set: int
    bounding_box: CAaBox

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
    height_map: Optional[List[float]] = None
    normal_data: Optional[List[float]] = None  # MCNR data
    liquid_heights: Optional[List[float]] = None
    liquid_flags: Optional[List[int]] = None
    texture_layers: Optional[List[TextureLayer]] = None  # MCLY data
    mcal_data: Optional[bytes] = None  # Raw MCAL chunk data

@dataclass
class MapTile:
    """Map tile information"""
    x: int
    y: int
    offset: int
    size: int
    flags: int
    async_id: int
    mcnk_data: Optional[Dict] = None

@dataclass
class ModelReference:
    """Model reference information"""
    path: str
    format_type: str  # 'alpha' or 'retail'
    name_id: int

@dataclass
class ChunkInfo:
    """Information about a chunk's location in a file"""
    name: bytes
    offset: int
    size: int
    data_offset: int

@dataclass
class TerrainFile:
    """Base class for terrain files (ADT/WDT)"""
    path: str
    file_type: str  # 'adt' or 'wdt'
    format_type: str  # 'alpha' or 'retail'
    version: int
    flags: Union[MCNKFlags, WDTFlags]
    map_name: str
    chunk_order: List[str]

@dataclass
class ADTFile(TerrainFile):
    """ADT file data"""
    textures: List[TextureInfo]
    m2_models: List[str]
    wmo_models: List[str]
    m2_placements: List[ModelPlacement]
    wmo_placements: List[WMOPlacement]
    mcnk_chunks: Dict[Tuple[int, int], MCNKInfo]
    subchunks: Dict[Tuple[int, int], Dict[str, any]]

@dataclass
class WDTFile(TerrainFile):
    """WDT file data"""
    tiles: Dict[Tuple[int, int], MapTile]
    m2_models: List[ModelReference]
    wmo_models: List[ModelReference]
    m2_placements: List[ModelPlacement]
    wmo_placements: List[WMOPlacement]
    is_global_wmo: bool
    chunk_offsets: Dict[str, ChunkInfo] = field(default_factory=dict)  # Store chunk offset information