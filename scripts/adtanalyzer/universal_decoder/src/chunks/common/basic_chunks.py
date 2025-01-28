"""
Common chunk decoders shared between formats
"""

import struct
from typing import Dict, Any, List
from .base_decoder import ChunkDecoder

class MVERDecoder(ChunkDecoder):
    """
    MVER chunk decoder - File version information
    Common between both formats
    """
    def __init__(self):
        super().__init__(b'MVER')

    def decode(self, data: bytes) -> Dict[str, Any]:
        self.validate_size(data, 4)
        version = struct.unpack('<I', data)[0]
        return {
            'version': version
        }

    def encode(self, data: Dict[str, Any]) -> bytes:
        return struct.pack('<I', data['version'])

class MCVTDecoder(ChunkDecoder):
    """
    MCVT chunk decoder - Height map data
    145 height values per chunk (9x9 grid + additional vertices)
    Common between both formats with minor differences in scale
    """
    def __init__(self):
        super().__init__(b'MCVT')

    def decode(self, data: bytes) -> Dict[str, Any]:
        # 145 floats = 580 bytes
        self.validate_size(data, 580)
        
        heights = []
        for i in range(0, 580, 4):
            height = struct.unpack('<f', data[i:i+4])[0]
            heights.append(height)
            
        return {
            'heights': heights,
            'grid_size': {
                'base': 9,  # 9x9 base grid
                'total': 145  # Including additional vertices
            }
        }

    def encode(self, data: Dict[str, Any]) -> bytes:
        heights = data['heights']
        if len(heights) != 145:
            raise ValueError(f"Expected 145 height values, got {len(heights)}")
        return struct.pack('<145f', *heights)

class MCNRDecoder(ChunkDecoder):
    """
    MCNR chunk decoder - Normal vectors
    Common between both formats
    """
    def __init__(self):
        super().__init__(b'MCNR')

    def decode(self, data: bytes) -> Dict[str, Any]:
        # 3 bytes per normal * 145 vertices = 435 bytes
        self.validate_size(data, 435)
        
        normals = []
        for i in range(0, 435, 3):
            # Convert from signed byte (-127 to 127) to float (-1 to 1)
            x = struct.unpack('b', data[i:i+1])[0] / 127.0
            y = struct.unpack('b', data[i+1:i+2])[0] / 127.0
            z = struct.unpack('b', data[i+2:i+3])[0] / 127.0
            normals.append({'x': x, 'y': y, 'z': z})
            
        return {
            'normals': normals,
            'grid_size': {
                'base': 9,
                'total': 145
            }
        }

    def encode(self, data: Dict[str, Any]) -> bytes:
        normals = data['normals']
        if len(normals) != 145:
            raise ValueError(f"Expected 145 normal vectors, got {len(normals)}")
            
        result = bytearray()
        for normal in normals:
            # Convert from float (-1 to 1) to signed byte (-127 to 127)
            x = int(normal['x'] * 127)
            y = int(normal['y'] * 127)
            z = int(normal['z'] * 127)
            result.extend(struct.pack('3b', x, y, z))
            
        return bytes(result)

class MCLYDecoder(ChunkDecoder):
    """
    MCLY chunk decoder - Texture layer definitions
    Basic structure common between formats, details may vary
    """
    def __init__(self):
        super().__init__(b'MCLY')

    def decode(self, data: bytes) -> Dict[str, Any]:
        if len(data) % 16 != 0:  # Each layer is 16 bytes
            raise ValueError(f"Invalid MCLY chunk size: {len(data)}")
            
        layers = []
        for i in range(0, len(data), 16):
            layer_data = data[i:i+16]
            texture_id, flags, offset_in_mcal, effect_id = struct.unpack('<4I', layer_data)
            
            layers.append({
                'texture_id': texture_id,
                'flags': flags,
                'offset_in_mcal': offset_in_mcal,
                'effect_id': effect_id,
                'flags_decoded': self._decode_flags(flags)
            })
            
        return {
            'layers': layers,
            'layer_count': len(layers)
        }

    def encode(self, data: Dict[str, Any]) -> bytes:
        result = bytearray()
        for layer in data['layers']:
            result.extend(struct.pack('<4I',
                layer['texture_id'],
                layer['flags'],
                layer['offset_in_mcal'],
                layer['effect_id']
            ))
        return bytes(result)

    def _decode_flags(self, flags: int) -> Dict[str, bool]:
        """Decode layer flags into human-readable format"""
        return {
            'use_alpha_map': bool(flags & 0x1),
            'alpha_compressed': bool(flags & 0x2),
            'use_height_texture': bool(flags & 0x4),
            'unknown_0x8': bool(flags & 0x8),
            'unknown_0x10': bool(flags & 0x10),
            'unknown_0x20': bool(flags & 0x20),
            'unknown_0x40': bool(flags & 0x40),
            'unknown_0x80': bool(flags & 0x80)
        }

class MTEXDecoder(ChunkDecoder):
    """
    MTEX chunk decoder - Texture filenames
    Common between both formats
    """
    def __init__(self):
        super().__init__(b'MTEX')

    def decode(self, data: bytes) -> Dict[str, Any]:
        textures = []
        pos = 0
        while pos < len(data):
            texture, next_pos = self.read_padded_string(data, pos)
            if texture:
                textures.append(texture)
            pos = next_pos
            
        return {
            'textures': textures,
            'texture_count': len(textures)
        }

    def encode(self, data: Dict[str, Any]) -> bytes:
        result = bytearray()
        for texture in data['textures']:
            result.extend(self.pack_string(texture))
        return bytes(result)