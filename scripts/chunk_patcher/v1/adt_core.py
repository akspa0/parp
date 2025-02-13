# adt_core.py
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import re

@dataclass
class ADTOffsets:
    x: int
    y: int
    z_offset: float = 0.0
    wdt_x_offset: float = 0.0
    wdt_y_offset: float = 0.0
    wdt_z_offset: float = 0.0
    xf: float = 0.0
    zf: float = 0.0

@dataclass
class ADTCoordinates:
    x: int
    y: int
    
    @classmethod
    def from_filename(cls, filename: str) -> Optional['ADTCoordinates']:
        match = re.search(r'_(\d+)_(\d+)\.adt$', filename, re.IGNORECASE)
        if match:
            return cls(int(match.group(1)), int(match.group(2)))
        return None

@dataclass
class MCNKInfo:
    offset: int
    size: int
    flags: int
    ix: int
    iy: int
    n_layers: int
    n_doodads: int
    holes: int
    layer_offset: int
    ref_offset: int
    alpha_offset: int
    shadow_offset: int
    height_offset: int

@dataclass
class ChunkOffsets:
    mddf_offset: int = 0
    modf_offset: int = 0
    mcnk_positions: List[Tuple[int, int]] = field(default_factory=list)