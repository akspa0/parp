#!/usr/bin/env python3
from dataclasses import dataclass
from typing import List
import struct
from enum import IntFlag

class MTXFFlags(IntFlag):
    """Texture flags used in MTXF"""
    TEXTURE_HORIZONTAL = 0x1
    TEXTURE_VERTICAL = 0x2
    TEXTURE_DANGEROUS = 0x4  # Used for lava/slime
    TEXTURE_PLATEAU = 0x8   # Higher Mask-value = Higher Priority

@dataclass
class FlightBox:
    """Flight boundary box with height limits"""
    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float

    @classmethod
    def from_bytes(cls, data: bytes) -> 'FlightBox':
        min_x, min_y, min_z, max_x, max_y, max_z = struct.unpack('<ffffff', data)
        return cls(min_x, min_y, min_z, max_x, max_y, max_z)

class MFBOChunk:
    """Flight bounds chunk parser"""
    def __init__(self, data: bytes):
        self.flight_boxes: List[FlightBox] = []
        self._parse(data)

    def _parse(self, data: bytes):
        # Each flight box is 24 bytes (6 floats)
        box_size = 24
        num_boxes = len(data) // box_size

        for i in range(num_boxes):
            offset = i * box_size
            box_data = data[offset:offset + box_size]
            self.flight_boxes.append(FlightBox.from_bytes(box_data))

    def is_point_in_bounds(self, x: float, y: float, z: float) -> bool:
        """Check if a point is within any flight box"""
        for box in self.flight_boxes:
            if (box.min_x <= x <= box.max_x and
                box.min_y <= y <= box.max_y and
                box.min_z <= z <= box.max_z):
                return True
        return False

    def get_max_height(self, x: float, y: float) -> float:
        """Get maximum flight height at given x,y coordinates"""
        max_height = float('-inf')
        for box in self.flight_boxes:
            if (box.min_x <= x <= box.max_x and
                box.min_y <= y <= box.max_y):
                max_height = max(max_height, box.max_z)
        return max_height if max_height != float('-inf') else 0.0

class MTXFChunk:
    """Texture flags chunk parser"""
    def __init__(self, data: bytes):
        self.texture_flags: List[MTXFFlags] = []
        self._parse(data)

    def _parse(self, data: bytes):
        # Each flag is a uint32
        flag_size = 4
        num_flags = len(data) // flag_size

        for i in range(num_flags):
            offset = i * flag_size
            flag_data = data[offset:offset + flag_size]
            flag_value = struct.unpack('<I', flag_data)[0]
            self.texture_flags.append(MTXFFlags(flag_value))

    def get_texture_flags(self, texture_index: int) -> MTXFFlags:
        """Get flags for texture at given index"""
        if 0 <= texture_index < len(self.texture_flags):
            return self.texture_flags[texture_index]
        return MTXFFlags(0)

    def is_texture_dangerous(self, texture_index: int) -> bool:
        """Check if texture is marked as dangerous (lava/slime)"""
        flags = self.get_texture_flags(texture_index)
        return bool(flags & MTXFFlags.TEXTURE_DANGEROUS)

    def get_texture_orientation(self, texture_index: int) -> tuple[bool, bool]:
        """Get texture orientation (horizontal, vertical)"""
        flags = self.get_texture_flags(texture_index)
        return (
            bool(flags & MTXFFlags.TEXTURE_HORIZONTAL),
            bool(flags & MTXFFlags.TEXTURE_VERTICAL)
        )

def example_usage():
    """Example usage of MFBO and MTXF chunks"""
    # Create example MFBO data (2 flight boxes)
    mfbo_data = bytearray()
    
    # Flight box 1: Simple cube from (0,0,0) to (100,100,100)
    mfbo_data.extend(struct.pack('<ffffff',
        0.0, 0.0, 0.0,      # min point
        100.0, 100.0, 100.0 # max point
    ))
    
    # Flight box 2: Higher altitude box
    mfbo_data.extend(struct.pack('<ffffff',
        50.0, 50.0, 100.0,    # min point
        150.0, 150.0, 200.0   # max point
    ))
    
    # Create example MTXF data (4 textures with different flags)
    mtxf_data = bytearray()
    
    # Texture 1: Normal ground (no special flags)
    mtxf_data.extend(struct.pack('<I', 0))
    
    # Texture 2: Horizontal texture (like water surface)
    mtxf_data.extend(struct.pack('<I', int(MTXFFlags.TEXTURE_HORIZONTAL)))
    
    # Texture 3: Dangerous texture (like lava)
    mtxf_data.extend(struct.pack('<I', int(MTXFFlags.TEXTURE_DANGEROUS)))
    
    # Texture 4: Plateau texture with vertical orientation
    mtxf_data.extend(struct.pack('<I', int(MTXFFlags.TEXTURE_PLATEAU | MTXFFlags.TEXTURE_VERTICAL)))
    
    # Parse chunks
    mfbo_chunk = MFBOChunk(mfbo_data)
    mtxf_chunk = MTXFChunk(mtxf_data)
    
    # Display results
    print("MFBO (Flight Bounds) Information:")
    for i, box in enumerate(mfbo_chunk.flight_boxes):
        print(f"\nFlight Box {i + 1}:")
        print(f"  Min Point: ({box.min_x}, {box.min_y}, {box.min_z})")
        print(f"  Max Point: ({box.max_x}, {box.max_y}, {box.max_z})")
    
    # Test some point checks
    test_points = [
        (50.0, 50.0, 50.0),    # Should be in bounds
        (200.0, 200.0, 200.0), # Should be out of bounds
        (75.0, 75.0, 150.0)    # Should be in bounds (in higher box)
    ]
    
    print("\nFlight Bound Checks:")
    for x, y, z in test_points:
        in_bounds = mfbo_chunk.is_point_in_bounds(x, y, z)
        max_height = mfbo_chunk.get_max_height(x, y)
        print(f"  Point ({x}, {y}, {z}):")
        print(f"    In Bounds: {in_bounds}")
        print(f"    Max Height: {max_height}")
    
    print("\nMTXF (Texture Flags) Information:")
    for i, flags in enumerate(mtxf_chunk.texture_flags):
        print(f"\nTexture {i}:")
        print(f"  Raw Flags: {flags}")
        horizontal, vertical = mtxf_chunk.get_texture_orientation(i)
        print(f"  Orientation: {'Horizontal' if horizontal else ''} {'Vertical' if vertical else ''}")
        print(f"  Dangerous: {mtxf_chunk.is_texture_dangerous(i)}")
        print(f"  Is Plateau: {bool(flags & MTXFFlags.TEXTURE_PLATEAU)}")

if __name__ == "__main__":
    example_usage()
