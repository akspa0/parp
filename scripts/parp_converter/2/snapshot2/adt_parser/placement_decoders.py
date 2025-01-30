#!/usr/bin/env python3
from dataclasses import dataclass
from typing import List, Optional, Tuple
import struct
from enum import IntFlag
import numpy as np

TILE_SIZE = 533.333333333
MAP_CORNER_OFFSET = 17066.0

class MDDFFlags(IntFlag):
    BIODOME = 0x1
    SHRUBBERY = 0x2
    UNK_4 = 0x4
    UNK_8 = 0x8
    UNK_10 = 0x10
    LIQUID_KNOWN = 0x20
    ENTRY_IS_FILEDATA_ID = 0x40
    UNK_100 = 0x100
    ACCEPT_PROJ_TEXTURES = 0x1000

class MODFFlags(IntFlag):
    DESTROYABLE = 0x1
    USE_LOD = 0x2
    HAS_SCALE = 0x4
    ENTRY_IS_FILEDATA_ID = 0x8
    USE_SETS_FROM_MWDS = 0x80

@dataclass
class Vector3D:
    x: float
    y: float
    z: float

    @classmethod
    def from_bytes(cls, data: bytes) -> 'Vector3D':
        return cls(*struct.unpack('<fff', data))

@dataclass
class AABox:
    """Axis-aligned bounding box"""
    min: Vector3D
    max: Vector3D

    @classmethod
    def from_bytes(cls, data: bytes) -> 'AABox':
        min_x, min_y, min_z = struct.unpack('<fff', data[:12])
        max_x, max_y, max_z = struct.unpack('<fff', data[12:24])
        return cls(
            Vector3D(min_x, min_y, min_z),
            Vector3D(max_x, max_y, max_z)
        )

@dataclass
class DoodadDef:
    """M2/Doodad placement definition (MDDF)"""
    name_id: int          # MMID reference or filedata id
    unique_id: int        # Should be unique across all loaded ADTs
    position: Vector3D    # Relative to map corner
    rotation: Vector3D    # Degrees
    scale: float         # 1024 = 1.0
    flags: MDDFFlags

    @classmethod
    def from_bytes(cls, data: bytes) -> 'DoodadDef':
        name_id, unique_id = struct.unpack('<II', data[:8])
        pos = Vector3D.from_bytes(data[8:20])
        rot = Vector3D.from_bytes(data[20:32])
        scale, flags = struct.unpack('<HH', data[32:36])
        return cls(
            name_id=name_id,
            unique_id=unique_id,
            position=pos,
            rotation=rot,
            scale=scale / 1024.0,
            flags=MDDFFlags(flags)
        )

    def create_placement_matrix(self) -> np.ndarray:
        """Create 4x4 placement matrix for M2"""
        # Convert to radians
        rx = np.radians(self.rotation.x)
        ry = np.radians(self.rotation.y)
        rz = np.radians(self.rotation.z)

        # Adjust position relative to map corner
        pos_x = 32 * TILE_SIZE - self.position.x
        pos_y = self.position.y
        pos_z = 32 * TILE_SIZE - self.position.z

        # Create transformation matrix
        matrix = np.identity(4)

        # Rotate coordinate system to Z-up
        matrix = matrix @ rotation_matrix_x(np.radians(90))
        matrix = matrix @ rotation_matrix_y(np.radians(90))

        # Translate
        matrix = matrix @ translation_matrix(pos_x, pos_y, pos_z)

        # Apply rotations
        matrix = matrix @ rotation_matrix_y(ry - np.radians(270))
        matrix = matrix @ rotation_matrix_z(-rx)
        matrix = matrix @ rotation_matrix_x(rz - np.radians(90))

        # Apply scale
        matrix = matrix @ scale_matrix(self.scale, self.scale, self.scale)

        return matrix

@dataclass
class MapObjDef:
    """WMO placement definition (MODF)"""
    name_id: int          # MWID reference or filedata id
    unique_id: int        # Should be unique across all loaded ADTs
    position: Vector3D    # Relative to map corner
    rotation: Vector3D    # Degrees
    extents: AABox       # Position + transformed WMO bounds
    flags: MODFFlags
    doodad_set: int      # WMO doodad set index
    name_set: int        # WMO name set index
    scale: float         # 1024 = 1.0 (Legion+)

    @classmethod
    def from_bytes(cls, data: bytes) -> 'MapObjDef':
        name_id, unique_id = struct.unpack('<II', data[:8])
        pos = Vector3D.from_bytes(data[8:20])
        rot = Vector3D.from_bytes(data[20:32])
        ext = AABox.from_bytes(data[32:56])
        flags, doodad_set, name_set, scale = struct.unpack('<HHHH', data[56:64])
        
        # Handle scale based on flags
        actual_scale = 1.0
        if MODFFlags.HAS_SCALE & flags:
            actual_scale = scale / 1024.0

        return cls(
            name_id=name_id,
            unique_id=unique_id,
            position=pos,
            rotation=rot,
            extents=ext,
            flags=MODFFlags(flags),
            doodad_set=doodad_set,
            name_set=name_set,
            scale=actual_scale
        )

    def create_placement_matrix(self) -> np.ndarray:
        """Create 4x4 placement matrix for WMO"""
        # Convert to radians
        rx = np.radians(self.rotation.x)
        ry = np.radians(self.rotation.y)
        rz = np.radians(self.rotation.z)

        # Adjust position relative to map corner
        pos_x = 32 * TILE_SIZE - self.position.x
        pos_y = self.position.y
        pos_z = 32 * TILE_SIZE - self.position.z

        # Create transformation matrix
        matrix = np.identity(4)

        # Rotate coordinate system to Z-up
        matrix = matrix @ rotation_matrix_x(np.radians(90))
        matrix = matrix @ rotation_matrix_y(np.radians(90))

        # Translate
        matrix = matrix @ translation_matrix(pos_x, pos_y, pos_z)

        # Apply rotations
        matrix = matrix @ rotation_matrix_y(ry - np.radians(270))
        matrix = matrix @ rotation_matrix_z(-rx)
        matrix = matrix @ rotation_matrix_x(rz - np.radians(90))

        if self.flags & MODFFlags.HAS_SCALE:
            matrix = matrix @ scale_matrix(self.scale, self.scale, self.scale)

        return matrix

def rotation_matrix_x(angle: float) -> np.ndarray:
    """Create rotation matrix around X axis"""
    return np.array([
        [1, 0, 0, 0],
        [0, np.cos(angle), -np.sin(angle), 0],
        [0, np.sin(angle), np.cos(angle), 0],
        [0, 0, 0, 1]
    ])

def rotation_matrix_y(angle: float) -> np.ndarray:
    """Create rotation matrix around Y axis"""
    return np.array([
        [np.cos(angle), 0, np.sin(angle), 0],
        [0, 1, 0, 0],
        [-np.sin(angle), 0, np.cos(angle), 0],
        [0, 0, 0, 1]
    ])

def rotation_matrix_z(angle: float) -> np.ndarray:
    """Create rotation matrix around Z axis"""
    return np.array([
        [np.cos(angle), -np.sin(angle), 0, 0],
        [np.sin(angle), np.cos(angle), 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1]
    ])

def translation_matrix(x: float, y: float, z: float) -> np.ndarray:
    """Create translation matrix"""
    return np.array([
        [1, 0, 0, x],
        [0, 1, 0, y],
        [0, 0, 1, z],
        [0, 0, 0, 1]
    ])

def scale_matrix(x: float, y: float, z: float) -> np.ndarray:
    """Create scale matrix"""
    return np.array([
        [x, 0, 0, 0],
        [0, y, 0, 0],
        [0, 0, z, 0],
        [0, 0, 0, 1]
    ])

class MDDFChunk:
    """Handler for MDDF (M2/Doodad placement) chunk"""
    def __init__(self, data: bytes):
        self.doodads: List[DoodadDef] = []
        self._parse(data)

    def _parse(self, data: bytes):
        entry_size = 36  # Size of each DoodadDef
        num_entries = len(data) // entry_size
        
        for i in range(num_entries):
            offset = i * entry_size
            doodad = DoodadDef.from_bytes(data[offset:offset + entry_size])
            self.doodads.append(doodad)

    def get_doodad_by_unique_id(self, unique_id: int) -> Optional[DoodadDef]:
        """Get doodad definition by its unique ID"""
        for doodad in self.doodads:
            if doodad.unique_id == unique_id:
                return doodad
        return None

class MODFChunk:
    """Handler for MODF (WMO placement) chunk"""
    def __init__(self, data: bytes):
        self.map_objects: List[MapObjDef] = []
        self._parse(data)

    def _parse(self, data: bytes):
        entry_size = 64  # Size of each MapObjDef
        num_entries = len(data) // entry_size
        
        for i in range(num_entries):
            offset = i * entry_size
            map_obj = MapObjDef.from_bytes(data[offset:offset + entry_size])
            self.map_objects.append(map_obj)

    def get_object_by_unique_id(self, unique_id: int) -> Optional[MapObjDef]:
        """Get map object definition by its unique ID"""
        for obj in self.map_objects:
            if obj.unique_id == unique_id:
                return obj
        return None

def example_usage():
    """Example usage of MDDF and MODF chunk handling"""
    # Create example MDDF chunk data
    mddf_data = bytearray()
    
    # Add one doodad definition
    mddf_data.extend(struct.pack('<II', 1000, 1))  # nameId, uniqueId
    mddf_data.extend(struct.pack('<fff', 1000.0, 200.0, 1000.0))  # position
    mddf_data.extend(struct.pack('<fff', 0.0, 90.0, 0.0))  # rotation
    mddf_data.extend(struct.pack('<HH', 1024, int(MDDFFlags.BIODOME)))  # scale, flags

    # Create example MODF chunk data
    modf_data = bytearray()
    
    # Add one map object definition
    modf_data.extend(struct.pack('<II', 2000, 1))  # nameId, uniqueId
    modf_data.extend(struct.pack('<fff', 2000.0, 300.0, 2000.0))  # position
    modf_data.extend(struct.pack('<fff', 0.0, 180.0, 0.0))  # rotation
    # Add bounding box
    modf_data.extend(struct.pack('<fff', -10.0, -10.0, -10.0))  # mins
    modf_data.extend(struct.pack('<fff', 10.0, 10.0, 10.0))    # maxs
    modf_data.extend(struct.pack('<HHHH',  # flags, doodadSet, nameSet, scale
        int(MODFFlags.HAS_SCALE), 0, 0, 1024))

    # Parse chunks
    mddf_chunk = MDDFChunk(mddf_data)
    modf_chunk = MODFChunk(modf_data)

    # Display results
    print("\nMDDF (Doodad) Placements:")
    for doodad in mddf_chunk.doodads:
        print(f"\nDoodad {doodad.unique_id}:")
        print(f"  Name ID: {doodad.name_id}")
        print(f"  Position: ({doodad.position.x}, {doodad.position.y}, {doodad.position.z})")
        print(f"  Rotation: ({doodad.rotation.x}°, {doodad.rotation.y}°, {doodad.rotation.z}°)")
        print(f"  Scale: {doodad.scale}")
        print(f"  Flags: {doodad.flags}")
        
        # Show placement matrix
        print("\nPlacement Matrix:")
        print(doodad.create_placement_matrix())

    print("\nMODF (WMO) Placements:")
    for map_obj in modf_chunk.map_objects:
        print(f"\nWMO {map_obj.unique_id}:")
        print(f"  Name ID: {map_obj.name_id}")
        print(f"  Position: ({map_obj.position.x}, {map_obj.position.y}, {map_obj.position.z})")
        print(f"  Rotation: ({map_obj.rotation.x}°, {map_obj.rotation.y}°, {map_obj.rotation.z}°)")
        print(f"  Scale: {map_obj.scale}")
        print(f"  Flags: {map_obj.flags}")
        print(f"  Doodad Set: {map_obj.doodad_set}")
        print(f"  Name Set: {map_obj.name_set}")
        print(f"  Bounds: Min({map_obj.extents.min.x}, {map_obj.extents.min.y}, {map_obj.extents.min.z})")
        print(f"          Max({map_obj.extents.max.x}, {map_obj.extents.max.y}, {map_obj.extents.max.z})")
        
        # Show placement matrix
        print("\nPlacement Matrix:")
        print(map_obj.create_placement_matrix())

if __name__ == "__main__":
    example_usage()
