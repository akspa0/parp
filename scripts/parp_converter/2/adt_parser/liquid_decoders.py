#!/usr/bin/env python3
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Union
import struct
import logging
from enum import IntFlag, IntEnum
from collections import defaultdict

logger = logging.getLogger(__name__)

# Constants
MAGMA_SCALE_ADT = 3.0 / 256.0
MAGMA_SCALE_WMO = 1.0 / 256.0

class LiquidType(IntEnum):
    NONE = 0
    OCEAN = 1
    MAGMA = 2
    SLIME = 3
    RIVER = 4
    WATER = 5  # Generic water
    MAGMA_WMO = 6

class LiquidFlags(IntFlag):
    RENDER = 0x0F
    CUSTOM_1 = 0x10
    CUSTOM_2 = 0x20
    NOT_LOW_DEPTH = 0x40  # Forced swimming
    FATIGUE = 0x80

class LiquidVertexFormat:
    """LiquidVertexFormat cases and their data structures"""
    CASE_0 = 0  # Height and Depth (float[], char[])
    CASE_1 = 1  # Height and UV (float[], uv_map_entry[])
    CASE_2 = 2  # Depth only (char[])
    CASE_3 = 3  # Height, UV, and Depth (float[], uv_map_entry[], char[])

@dataclass
class Vector3D:
    x: float
    y: float
    z: float

    @classmethod
    def from_bytes(cls, data: bytes) -> 'Vector3D':
        return cls(*struct.unpack('<fff', data))

@dataclass
class Sphere:
    center: Vector3D
    radius: float

    @classmethod
    def from_bytes(cls, data: bytes) -> 'Sphere':
        x, y, z, radius = struct.unpack('<ffff', data)
        return cls(Vector3D(x, y, z), radius)

@dataclass
class WaterVertex:
    """Water vertex structure (SWVert)"""
    depth: int
    flow0_pct: int
    flow1_pct: int
    height: float

    @classmethod
    def from_bytes(cls, data: bytes) -> 'WaterVertex':
        depth, flow0, flow1, filler, height = struct.unpack('<BBBBf', data)
        return cls(depth, flow0, flow1, height)

@dataclass
class OceanVertex:
    """Ocean vertex structure (SOVert)"""
    depth: int
    foam: int
    wet: int
    height: float = 0.0  # Height inherited from base vertex

    @classmethod
    def from_bytes(cls, data: bytes) -> 'OceanVertex':
        depth, foam, wet, filler = struct.unpack('<BBBB', data)
        return cls(depth, foam, wet)

@dataclass
class MagmaVertex:
    """Magma vertex structure (SMVert)"""
    s: int
    t: int
    height: float

    @property
    def tex_coord_s(self) -> float:
        """Get adjusted texture coordinate S"""
        return self.s * MAGMA_SCALE_ADT

    @property
    def tex_coord_t(self) -> float:
        """Get adjusted texture coordinate T"""
        return self.t * MAGMA_SCALE_ADT

    @classmethod
    def from_bytes(cls, data: bytes) -> 'MagmaVertex':
        s, t, height = struct.unpack('<HHf', data)
        return cls(s, t, height)

@dataclass
class LiquidFlow:
    """Water flow information (SWFlowv)"""
    sphere: Sphere
    direction: Vector3D
    velocity: float
    amplitude: float
    frequency: float

    @classmethod
    def from_bytes(cls, data: bytes) -> 'LiquidFlow':
        # 28 bytes total: sphere(16) + vector3(12) + 3 floats(12)
        sphere_data = data[:16]
        dir_data = data[16:28]
        velocity, amplitude, frequency = struct.unpack('<fff', data[28:40])
        
        return cls(
            sphere=Sphere.from_bytes(sphere_data),
            direction=Vector3D.from_bytes(dir_data),
            velocity=velocity,
            amplitude=amplitude,
            frequency=frequency
        )

@dataclass
class UVMapEntry:
    """Texture coordinate entry for liquid"""
    x: int  # divided by 8 for shaders
    y: int

    @classmethod
    def from_bytes(cls, data: bytes) -> 'UVMapEntry':
        x, y = struct.unpack('<HH', data)
        return cls(x, y)

    @property
    def shader_x(self) -> float:
        return self.x / 8.0

    @property
    def shader_y(self) -> float:
        return self.y / 8.0

@dataclass
class MH2OAttributes:
    """MH2O chunk attributes"""
    fishable: int  # uint64 bitmask
    deep: int      # uint64 bitmask

    @classmethod
    def from_bytes(cls, data: bytes) -> 'MH2OAttributes':
        fishable, deep = struct.unpack('<QQ', data)
        return cls(fishable, deep)

    def is_fishable(self, x: int, y: int) -> bool:
        """Check if position is fishable (x,y in 0-7 range)"""
        if 0 <= x < 8 and 0 <= y < 8:
            return bool(self.fishable & (1 << (y * 8 + x)))
        return False

    def is_deep(self, x: int, y: int) -> bool:
        """Check if position is deep water (x,y in 0-7 range)"""
        if 0 <= x < 8 and 0 <= y < 8:
            return bool(self.deep & (1 << (y * 8 + x)))
        return False

class MCLQLiquid:
    """Legacy liquid data from MCLQ chunk"""
    def __init__(self, data: bytes, liquid_type: LiquidType):
        self.liquid_type = liquid_type
        self.vertices: List[Union[WaterVertex, OceanVertex, MagmaVertex]] = []
        self.tiles: List[List[int]] = []  # 8x8 grid
        self.flows: List[LiquidFlow] = []
        
        self._parse(data)

    def _parse(self, data: bytes) -> None:
        offset = 0
        
        # Parse vertices (9x9 grid)
        vertex_size = 8  # All vertex types are 8 bytes
        for _ in range(81):  # 9x9 grid
            if self.liquid_type == LiquidType.OCEAN:
                vertex = OceanVertex.from_bytes(data[offset:offset+vertex_size])
            elif self.liquid_type == LiquidType.MAGMA:
                vertex = MagmaVertex.from_bytes(data[offset:offset+vertex_size])
            else:  # Water/River
                vertex = WaterVertex.from_bytes(data[offset:offset+vertex_size])
            
            self.vertices.append(vertex)
            offset += vertex_size

        # Parse tiles (8x8 grid)
        for row in range(8):
            tile_row = []
            for col in range(8):
                tile_flags = data[offset]
                tile_row.append(tile_flags)
                offset += 1
            self.tiles.append(tile_row)

        # Parse flow information
        num_flows = struct.unpack('<I', data[offset:offset+4])[0]
        offset += 4

        # Always read 2 flows regardless of num_flows
        for _ in range(2):
            if offset + 40 <= len(data):  # 40 bytes per flow
                flow = LiquidFlow.from_bytes(data[offset:offset+40])
                self.flows.append(flow)
                offset += 40

    def get_vertex(self, x: int, y: int) -> Optional[Union[WaterVertex, OceanVertex, MagmaVertex]]:
        """Get vertex at specific coordinates (0-8)"""
        if 0 <= x < 9 and 0 <= y < 9:
            return self.vertices[y * 9 + x]
        return None

    def get_tile(self, x: int, y: int) -> Optional[int]:
        """Get tile flags at specific coordinates (0-7)"""
        if 0 <= x < 8 and 0 <= y < 8:
            return self.tiles[y][x]
        return None

    def is_tile_rendered(self, x: int, y: int) -> bool:
        """Check if tile should be rendered"""
        tile = self.get_tile(x, y)
        return tile is not None and (tile & 0x0F) not in {0x0F, 0x08}

@dataclass
class MH2OInstance:
    """MH2O liquid instance data"""
    liquid_type: int
    lvf: int  # LiquidVertexFormat for WotLK
    min_height_level: float
    max_height_level: float
    x_offset: int
    y_offset: int
    width: int
    height: int
    exists_bitmap: Optional[bytes]
    vertex_data: Optional[bytes]
    vertex_format: int  # Determined from data size

    @classmethod
    def from_bytes(cls, data: bytes, chunk_data: bytes, is_wotlk: bool = True) -> 'MH2OInstance':
        liquid_type, lvf = struct.unpack('<HH', data[:4])
        min_height, max_height = struct.unpack('<ff', data[4:12])
        x_offset, y_offset, width, height = struct.unpack('<BBBB', data[12:16])
        offset_exists, offset_vertex = struct.unpack('<II', data[16:24])

        # Handle exists bitmap
        exists_bitmap = None
        if offset_exists:
            bitmap_size = (width * height + 7) // 8
            exists_bitmap = chunk_data[offset_exists:offset_exists + bitmap_size]

        # Handle vertex data
        vertex_data = None
        vertex_format = -1
        if offset_vertex:
            # Find next data offset to determine size
            next_offset = len(chunk_data)
            vertex_count = (width + 1) * (height + 1)
            data_size = next_offset - offset_vertex
            
            if data_size > 0:
                vertex_data = chunk_data[offset_vertex:offset_vertex + data_size]
                # Determine format based on size per vertex
                size_per_vertex = data_size // vertex_count
                vertex_format = {
                    5: LiquidVertexFormat.CASE_0,  # float + char
                    8: LiquidVertexFormat.CASE_1,  # float + 2 uint16
                    1: LiquidVertexFormat.CASE_2,  # char only
                    9: LiquidVertexFormat.CASE_3   # float + 2 uint16 + char
                }.get(size_per_vertex, -1)

        return cls(
            liquid_type=liquid_type,
            lvf=lvf,
            min_height_level=min_height,
            max_height_level=max_height,
            x_offset=x_offset,
            y_offset=y_offset,
            width=width,
            height=height,
            exists_bitmap=exists_bitmap,
            vertex_data=vertex_data,
            vertex_format=vertex_format
        )

    def get_vertex_data(self) -> Tuple[Optional[List[float]], Optional[List[UVMapEntry]], Optional[List[int]]]:
        """Returns (heightmap, uvmap, depthmap) based on vertex format"""
        if not self.vertex_data:
            return None, None, None

        vertex_count = (self.width + 1) * (self.height + 1)
        heightmap = []
        uvmap = []
        depthmap = []

        offset = 0
        if self.vertex_format in (LiquidVertexFormat.CASE_0, LiquidVertexFormat.CASE_1, LiquidVertexFormat.CASE_3):
            # Read heightmap
            for i in range(vertex_count):
                height = struct.unpack('<f', self.vertex_data[offset:offset+4])[0]
                heightmap.append(height)
                offset += 4

        if self.vertex_format in (LiquidVertexFormat.CASE_1, LiquidVertexFormat.CASE_3):
            # Read UV map
            for i in range(vertex_count):
                uv = UVMapEntry.from_bytes(self.vertex_data[offset:offset+4])
                uvmap.append(uv)
                offset += 4

        if self.vertex_format in (LiquidVertexFormat.CASE_0, LiquidVertexFormat.CASE_2, LiquidVertexFormat.CASE_3):
            # Read depthmap
            for i in range(vertex_count):
                depth = self.vertex_data[offset]
                depthmap.append(depth)
                offset += 1

        return heightmap or None, uvmap or None, depthmap or None

    def is_tile_visible(self, x: int, y: int) -> bool:
        """Check if liquid tile should be rendered"""
        if not self.exists_bitmap:
            return True  # If no bitmap, all tiles exist
            
        local_x = x - self.x_offset
        local_y = y - self.y_offset
        
        if (0 <= local_x < self.width and 
            0 <= local_y < self.height):
            byte_index = (local_y * self.width + local_x) // 8
            bit_index = (local_y * self.width + local_x) % 8
            return bool(self.exists_bitmap[byte_index] & (1 << bit_index))
            
        return False

class MH2OChunk:
    """Handler for MH2O chunk data"""
    def __init__(self, data: bytes):
        self.chunks: List[Tuple[int, int, List[MH2OInstance]]] = []
        self.attributes: Dict[Tuple[int, int], MH2OAttributes] = {}
        self._parse(data)

    def _parse(self, data: bytes):
        # Parse header entries (256 SMLiquidChunk structures)
        header_size = 256 * 12  # 256 entries * 12 bytes each
        for i in range(256):
            offset = i * 12
            chunk_data = data[offset:offset + 12]
            offset_instances, layer_count, offset_attributes = struct.unpack('<III', chunk_data)
            
            if layer_count > 0:
                x, y = i % 16, i // 16
                instances = []
                
                # Parse instances
                for j in range(layer_count):
                    instance_data = data[offset_instances + j * 24:offset_instances + (j + 1) * 24]
                    instance = MH2OInstance.from_bytes(instance_data, data)
                    instances.append(instance)
                
                self.chunks.append((x, y, instances))
                
                # Parse attributes if present
                if offset_attributes:
                    attr_data = data[offset_attributes:offset_attributes + 16]
                    self.attributes[(x, y)] = MH2OAttributes.from_bytes(attr_data)

    def get_liquid_instances(self, x: int, y: int) -> List[MH2OInstance]:
        """Get liquid instances for chunk coordinates"""
        for chunk_x, chunk_y, instances in self.chunks:
            if chunk_x == x and chunk_y == y:
                return instances
        return []

    def get_attributes(self, x: int, y: int) -> Optional[MH2OAttributes]:
        """Get attributes for chunk coordinates"""
        return self.attributes.get((x, y))

class LiquidManager:
    """Manages both MCLQ and MH2O liquid data"""
    
    def __init__(self):
        self.legacy_liquids: Dict[int, MCLQLiquid] = {}  # MCLQ data
        self.modern_liquids: Dict[int, MH2OChunk] = {}   # MH2O data

    def load_legacy_liquid(self, chunk_id: int, data: bytes, liquid_type: LiquidType) -> None:
        """Load legacy MCLQ liquid data"""
        try:
            self.legacy_liquids[chunk_id] = MCLQLiquid(data, liquid_type)
        except Exception as e:
            logger.error(f"Failed to load legacy liquid data for chunk {chunk_id}: {e}")

    def load_modern_liquid(self, chunk_id: int, data: bytes) -> None:
        """Load modern MH2O liquid data"""
        try:
            self.modern_liquids[chunk_id] = MH2OChunk(data)
        except Exception as e:
            logger.error(f"Failed to load modern liquid data for chunk {chunk_id}: {e}")

    def has_liquid(self, chunk_id: int) -> bool:
        """Check if chunk has any liquid data"""
        return chunk_id in self.legacy_liquids or chunk_id in self.modern_liquids

    def get_liquid_data(self, chunk_id: int) -> Optional[Union[MCLQLiquid, MH2OChunk]]:
        """Get liquid data for chunk, preferring modern format if available"""
        return self.modern_liquids.get(chunk_id) or self.legacy_liquids.get(chunk_id)

    def analyze_liquid_coverage(self) -> Dict[str, Dict[str, int]]:
        """Analyze liquid coverage and types for both formats"""
        stats = {
            'legacy': {
                'total_chunks': len(self.legacy_liquids),
                'liquid_types': defaultdict(int),
                'with_flows': sum(1 for liquid in self.legacy_liquids.values() if liquid.flows)
            },
            'modern': {
                'total_chunks': len(self.modern_liquids),
                'total_instances': 0,
                'chunks_with_attributes': 0,
                'liquid_types': defaultdict(int),
                'vertex_formats': defaultdict(int)
            }
        }
        
        # Analyze legacy liquids
        for liquid in self.legacy_liquids.values():
            stats['legacy']['liquid_types'][liquid.liquid_type.name] += 1
            
        # Analyze modern liquids
        for chunk in self.modern_liquids.values():
            stats['modern']['chunks_with_attributes'] += len(chunk.attributes)
            for _, _, instances in chunk.chunks:
                stats['modern']['total_instances'] += len(instances)
                for instance in instances:
                    stats['modern']['liquid_types'][instance.liquid_type] += 1
                    stats['modern']['vertex_formats'][instance.vertex_format] += 1
                
        return stats

def example_usage():
    """Example usage of both MCLQ and MH2O decoders"""
    # Create manager
    manager = LiquidManager()
    
    # Example MCLQ data
    legacy_data = bytearray()
    # Add vertex data (9x9 grid of water vertices)
    for _ in range(81):
        legacy_data.extend(struct.pack('<BBBBf', 
            10,     # depth
            0,      # flow0
            0,      # flow1
            0,      # filler
            0.0     # height
        ))
    # Add tile data (8x8 grid)
    for _ in range(64):
        legacy_data.append(LiquidType.WATER)
    # Add flow data
    legacy_data.extend(struct.pack('<I', 2))  # nFlowvs = 2
    # Add 2 flows
    for _ in range(2):
        legacy_data.extend(struct.pack('<ffff', 0.0, 0.0, 0.0, 1.0))  # sphere
        legacy_data.extend(struct.pack('<fff', 1.0, 0.0, 0.0))        # direction
        legacy_data.extend(struct.pack('<fff', 1.0, 0.5, 1.0))        # flow params
    
    # Example MH2O data
    modern_data = bytearray()
    # Add header (256 entries)
    for i in range(256):
        if i == 0:  # Add one liquid instance
            modern_data.extend(struct.pack('<III', 
                256 * 12,  # offset to instances
                1,         # one layer
                256 * 12 + 24  # offset to attributes
            ))
        else:
            modern_data.extend(struct.pack('<III', 0, 0, 0))
    
    # Add instance data
    modern_data.extend(struct.pack('<HHffBBBBII',
        LiquidType.WATER,  # liquid_type
        0,                 # lvf
        0.0,              # min_height
        1.0,              # max_height
        0,                # x_offset
        0,                # y_offset
        8,                # width
        8,                # height
        0,                # exists_bitmap offset
        0                 # vertex_data offset
    ))
    
    # Add attributes
    modern_data.extend(struct.pack('<QQ', 
        0xFFFFFFFFFFFFFFFF,  # all fishable
        0                    # none deep
    ))
    
    # Load data
    manager.load_legacy_liquid(0, bytes(legacy_data), LiquidType.WATER)
    manager.load_modern_liquid(1, bytes(modern_data))
    
    # Analyze results
    stats = manager.analyze_liquid_coverage()
    print("\nLiquid Analysis:")
    for format_name, format_stats in stats.items():
        print(f"\n{format_name.upper()} format:")
        for key, value in format_stats.items():
            print(f"  {key}: {value}")

if __name__ == "__main__":
    example_usage()
