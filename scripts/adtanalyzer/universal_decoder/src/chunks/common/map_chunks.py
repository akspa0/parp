"""
Map-specific chunk decoders (WDT/ADT)
"""

import struct
from typing import Dict, Any, List
from .base_decoder import ChunkDecoder, Vector3D

class MPHDDecoder(ChunkDecoder):
    """
    MPHD chunk decoder - Map header
    Contains map flags and settings
    """
    def __init__(self):
        super().__init__(b'MPHD')

    def decode(self, data: bytes) -> Dict[str, Any]:
        self.validate_size(data, 32)
        
        flags, something = struct.unpack('<II', data[0:8])
        unused = list(struct.unpack('<5I', data[8:28]))
        map_id = struct.unpack('<I', data[28:32])[0]
        
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
        
        return {
            'flags': flags,
            'flags_decoded': flags_decoded,
            'map_id': map_id,
            'unused_fields': unused
        }

    def encode(self, data: Dict[str, Any]) -> bytes:
        result = bytearray()
        result.extend(struct.pack('<I', data['flags']))
        result.extend(struct.pack('<I', 0))  # something
        result.extend(struct.pack('<5I', *data.get('unused_fields', [0]*5)))
        result.extend(struct.pack('<I', data['map_id']))
        return bytes(result)

class MAINDecoder(ChunkDecoder):
    """
    MAIN chunk decoder - Map tiles array
    Contains 64x64 grid of map tile information
    """
    def __init__(self):
        super().__init__(b'MAIN')

    def decode(self, data: bytes) -> Dict[str, Any]:
        tiles = []
        pos = 0
        
        for y in range(64):
            row = []
            for x in range(64):
                if pos + 8 > len(data):
                    break
                    
                flags, async_id = struct.unpack('<II', data[pos:pos+8])
                row.append({
                    'x': x,
                    'y': y,
                    'flags': flags,
                    'async_id': async_id,
                    'has_data': bool(flags & 0x1),
                    'flags_decoded': {
                        'has_adt': bool(flags & 0x1),
                        'loaded': bool(flags & 0x2),
                        'unknown_0x4': bool(flags & 0x4),
                        'unknown_0x8': bool(flags & 0x8)
                    }
                })
                pos += 8
            tiles.append(row)
            
        return {
            'grid_size': {'x': 64, 'y': 64},
            'tiles': tiles,
            'active_tiles': sum(1 for row in tiles for tile in row if tile['has_data'])
        }

    def encode(self, data: Dict[str, Any]) -> bytes:
        result = bytearray()
        for row in data['tiles']:
            for tile in row:
                result.extend(struct.pack('<II', tile['flags'], tile['async_id']))
        return bytes(result)

class ModelNameDecoder(ChunkDecoder):
    """Base class for model name chunks (MDNM/MONM/MMDX/MWMO)"""
    
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

class MDNMDecoder(ModelNameDecoder):
    """MDNM chunk decoder - M2 model filenames (Alpha)"""
    def __init__(self):
        super().__init__(b'MDNM')

class MONMDecoder(ModelNameDecoder):
    """MONM chunk decoder - WMO model filenames (Alpha)"""
    def __init__(self):
        super().__init__(b'MONM')

class MMDXDecoder(ModelNameDecoder):
    """MMDX chunk decoder - M2 model filenames (Retail)"""
    def __init__(self):
        super().__init__(b'MMDX')

class MWMODecoder(ModelNameDecoder):
    """MWMO chunk decoder - WMO model filenames (Retail)"""
    def __init__(self):
        super().__init__(b'MWMO')

class ModelIndexDecoder(ChunkDecoder):
    """Base class for model index chunks (MMID/MWID)"""
    
    def decode(self, data: bytes) -> Dict[str, Any]:
        count = len(data) // 4
        indices = list(struct.unpack(f'<{count}I', data))
        return {
            'indices': indices,
            'count': count
        }

    def encode(self, data: Dict[str, Any]) -> bytes:
        return struct.pack(f'<{len(data["indices"])}I', *data['indices'])

class MMIDDecoder(ModelIndexDecoder):
    """MMID chunk decoder - M2 model indices"""
    def __init__(self):
        super().__init__(b'MMID')

class MWIDDecoder(ModelIndexDecoder):
    """MWID chunk decoder - WMO model indices"""
    def __init__(self):
        super().__init__(b'MWID')

class MDDFDecoder(ChunkDecoder):
    """
    MDDF chunk decoder - M2 model placements
    Contains placement information for M2 models
    """
    def __init__(self):
        super().__init__(b'MDDF')

    def decode(self, data: bytes) -> Dict[str, Any]:
        entries = []
        pos = 0
        while pos + 36 <= len(data):
            name_id, unique_id = struct.unpack('<II', data[pos:pos+8])
            position = self.read_vec3d(data, pos+8)
            rotation = self.read_vec3d(data, pos+20)
            scale, flags = struct.unpack('<HH', data[pos+32:pos+36])
            
            entries.append({
                'name_id': name_id,
                'unique_id': unique_id,
                'position': position.to_dict(),
                'rotation': rotation.to_dict(),
                'scale': scale / 1024.0,  # Convert to float scale
                'flags': flags
            })
            pos += 36
            
        return {
            'entries': entries,
            'count': len(entries)
        }

    def encode(self, data: Dict[str, Any]) -> bytes:
        result = bytearray()
        for entry in data['entries']:
            result.extend(struct.pack('<II', entry['name_id'], entry['unique_id']))
            result.extend(self.pack_vec3d(Vector3D(**entry['position'])))
            result.extend(self.pack_vec3d(Vector3D(**entry['rotation'])))
            result.extend(struct.pack('<HH', 
                int(entry['scale'] * 1024),
                entry['flags']
            ))
        return bytes(result)

class MODFDecoder(ChunkDecoder):
    """
    MODF chunk decoder - WMO model placements
    Contains placement information for WMO models
    """
    def __init__(self):
        super().__init__(b'MODF')

    def decode(self, data: bytes) -> Dict[str, Any]:
        entries = []
        pos = 0
        while pos + 64 <= len(data):
            name_id, unique_id = struct.unpack('<II', data[pos:pos+8])
            position = self.read_vec3d(data, pos+8)
            rotation = self.read_vec3d(data, pos+20)
            bounds_min = self.read_vec3d(data, pos+32)
            bounds_max = self.read_vec3d(data, pos+44)
            flags, doodad_set, name_set, scale = struct.unpack('<HHHH', data[pos+56:pos+64])
            
            entries.append({
                'name_id': name_id,
                'unique_id': unique_id,
                'position': position.to_dict(),
                'rotation': rotation.to_dict(),
                'bounds': {
                    'min': bounds_min.to_dict(),
                    'max': bounds_max.to_dict()
                },
                'flags': flags,
                'doodad_set': doodad_set,
                'name_set': name_set,
                'scale': scale / 1024.0  # Convert to float scale
            })
            pos += 64
            
        return {
            'entries': entries,
            'count': len(entries)
        }

    def encode(self, data: Dict[str, Any]) -> bytes:
        result = bytearray()
        for entry in data['entries']:
            result.extend(struct.pack('<II', entry['name_id'], entry['unique_id']))
            result.extend(self.pack_vec3d(Vector3D(**entry['position'])))
            result.extend(self.pack_vec3d(Vector3D(**entry['rotation'])))
            result.extend(self.pack_vec3d(Vector3D(**entry['bounds']['min'])))
            result.extend(self.pack_vec3d(Vector3D(**entry['bounds']['max'])))
            result.extend(struct.pack('<HHHH',
                entry['flags'],
                entry['doodad_set'],
                entry['name_set'],
                int(entry['scale'] * 1024)
            ))
        return bytes(result)