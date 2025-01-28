"""
Alpha format specific chunk decoders
"""

import struct
from typing import Dict, Any, List
from ..common.base_decoder import ChunkDecoder, Vector3D

class AlphaMPHDDecoder(ChunkDecoder):
    """
    MPHD chunk decoder - Map header (Alpha format)
    Different structure from retail format
    """
    def __init__(self):
        super().__init__(b'MPHD')

    def decode(self, data: bytes) -> Dict[str, Any]:
        # Alpha format has a 128-byte header
        self.validate_size(data, 128)
        
        flags = struct.unpack('<I', data[0:4])[0]
        
        # Decode flags
        flags_decoded = {
            'wmo_only': bool(flags & 0x1),
            'no_terrain': bool(flags & 0x2),
            'unknown_0x4': bool(flags & 0x4),
            'unknown_0x8': bool(flags & 0x8),
            'unknown_0x10': bool(flags & 0x10),
            'unknown_0x20': bool(flags & 0x20),
            'unknown_0x40': bool(flags & 0x40),
            'unknown_0x80': bool(flags & 0x80)
        }
        
        # Rest of the header data (may contain additional fields)
        extra_data = data[4:]
        
        return {
            'flags': flags,
            'flags_decoded': flags_decoded,
            'extra_data_size': len(extra_data),
            'raw_extra_data': extra_data.hex()
        }

    def encode(self, data: Dict[str, Any]) -> bytes:
        result = bytearray()
        result.extend(struct.pack('<I', data['flags']))
        # Pad to 128 bytes
        result.extend(b'\0' * 124)
        return bytes(result)

class AlphaMAINDecoder(ChunkDecoder):
    """
    MAIN chunk decoder - Map tiles array (Alpha format)
    Different structure from retail format
    """
    def __init__(self):
        super().__init__(b'MAIN')

    def decode(self, data: bytes) -> Dict[str, Any]:
        entries = []
        pos = 0
        
        # Each tile entry is 32 bytes in Alpha format
        while pos + 32 <= len(data):
            # Unpack tile data
            offset, size, flags, async_id = struct.unpack('<4I', data[pos:pos+16])
            # Skip 16 bytes of padding/unused data
            pos += 32
            
            # Calculate grid coordinates
            y = len(entries) // 64
            x = len(entries) % 64
            
            # Create tile entry
            entry = {
                'offset': offset,
                'size': size,
                'flags': flags,
                'async_id': async_id,
                'coordinates': {'x': x, 'y': y},
                'has_data': bool(flags & 0x1),
                'flags_decoded': {
                    'has_adt': bool(flags & 0x1),
                    'loaded': bool(flags & 0x2),
                    'unknown_0x4': bool(flags & 0x4),
                    'unknown_0x8': bool(flags & 0x8)
                }
            }
            entries.append(entry)
        
        # Organize into 64x64 grid
        grid = []
        for y in range(64):
            row = []
            for x in range(64):
                idx = y * 64 + x
                if idx < len(entries):
                    entry = entries[idx]
                    tile = {
                        'x': x,
                        'y': y,
                        'flags': entry['flags'],
                        'flags_decoded': entry['flags_decoded'],
                        'has_data': entry['has_data'],
                        'offset': entry['offset'],
                        'size': entry['size'],
                        'async_id': entry['async_id']
                    }
                    row.append(tile)
                else:
                    # Fill with empty tile if data is incomplete
                    row.append({
                        'x': x,
                        'y': y,
                        'flags': 0,
                        'flags_decoded': {
                            'has_adt': False,
                            'loaded': False,
                            'unknown_0x4': False,
                            'unknown_0x8': False
                        },
                        'has_data': False,
                        'offset': 0,
                        'size': 0,
                        'async_id': 0
                    })
            grid.append(row)
        
        return {
            'tiles': grid,
            'active_tiles': sum(1 for entry in entries if entry['has_data'])
        }

    def encode(self, data: Dict[str, Any]) -> bytes:
        result = bytearray()
        for row in data['tiles']:
            for tile in row:
                result.extend(struct.pack('<4I',
                    tile['offset'],
                    tile['size'],
                    tile['flags'],
                    tile['async_id']
                ))
                # Add 16 bytes padding/unused data
                result.extend(b'\0' * 16)
        return bytes(result)

class AlphaMDNMDecoder(ChunkDecoder):
    """
    MDNM chunk decoder - M2 model filenames (Alpha format)
    Uses simple null-terminated string list
    """
    def __init__(self):
        super().__init__(b'MDNM')

    def decode(self, data: bytes) -> Dict[str, Any]:
        names = []
        pos = 0
        while pos < len(data):
            name, next_pos = self.read_padded_string(data, pos)
            if name:
                names.append(name)
            pos = next_pos
            
        return {
            'names': names,
            'count': len(names)
        }

    def encode(self, data: Dict[str, Any]) -> bytes:
        result = bytearray()
        for name in data['names']:
            result.extend(self.pack_string(name))
        return bytes(result)

class AlphaMONMDecoder(ChunkDecoder):
    """
    MONM chunk decoder - WMO model filenames (Alpha format)
    Uses simple null-terminated string list
    """
    def __init__(self):
        super().__init__(b'MONM')

    def decode(self, data: bytes) -> Dict[str, Any]:
        names = []
        pos = 0
        while pos < len(data):
            name, next_pos = self.read_padded_string(data, pos)
            if name:
                names.append(name)
            pos = next_pos
            
        return {
            'names': names,
            'count': len(names)
        }

    def encode(self, data: Dict[str, Any]) -> bytes:
        result = bytearray()
        for name in data['names']:
            result.extend(self.pack_string(name))
        return bytes(result)

class AlphaMAOCDecoder(ChunkDecoder):
    """
    MAOC chunk decoder - Map object coordinates (Alpha format)
    Contains coordinates for models
    """
    def __init__(self):
        super().__init__(b'MAOC')

    def decode(self, data: bytes) -> Dict[str, Any]:
        coordinates = []
        pos = 0
        while pos + 12 <= len(data):
            coord = self.read_vec3d(data, pos)
            coordinates.append(coord.to_dict())
            pos += 12
            
        return {
            'coordinates': coordinates,
            'count': len(coordinates)
        }

    def encode(self, data: Dict[str, Any]) -> bytes:
        result = bytearray()
        for coord in data['coordinates']:
            result.extend(self.pack_vec3d(Vector3D(**coord)))
        return bytes(result)

class AlphaMAOFDecoder(ChunkDecoder):
    """
    MAOF chunk decoder - Map object flags (Alpha format)
    Contains flags for models
    """
    def __init__(self):
        super().__init__(b'MAOF')

    def decode(self, data: bytes) -> Dict[str, Any]:
        count = len(data) // 4
        flags = list(struct.unpack(f'<{count}I', data))
        
        decoded_flags = []
        for flag in flags:
            decoded_flags.append({
                'raw_value': flag,
                'flags_decoded': {
                    'is_m2': bool(flag & 0x1),
                    'unknown_0x2': bool(flag & 0x2),
                    'unknown_0x4': bool(flag & 0x4),
                    'unknown_0x8': bool(flag & 0x8)
                }
            })
            
        return {
            'flags': flags,
            'decoded_flags': decoded_flags,
            'count': count
        }

    def encode(self, data: Dict[str, Any]) -> bytes:
        return struct.pack(f'<{len(data["flags"])}I', *data['flags'])