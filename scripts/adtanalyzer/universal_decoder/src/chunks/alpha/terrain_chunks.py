"""
Alpha format specific terrain chunk decoders
"""

import struct
from typing import Dict, Any, List
from ..common.base_decoder import ChunkDecoder, Vector3D

class AlphaMCNKDecoder(ChunkDecoder):
    """
    MCNK chunk decoder - Map chunk (Alpha format)
    Different structure from retail format
    
    Alpha MCNK has a simplified 16-byte header followed by:
    - MCVT: 145 float values (9x9 + 8x8 grid) for heightmap
    - MCLY: n_layers * 8 bytes for layer info
    - MCRF: n_doodad_refs * 4 bytes for doodad references
    - MCLQ: Liquid data (if present)
    """
    def __init__(self):
        super().__init__(b'MCNK')

    def decode(self, data: bytes) -> Dict[str, Any]:
        if len(data) < 16:
            raise ValueError("Alpha MCNK chunk too small")
            
        # Parse header
        flags, area_id, n_layers, n_doodad_refs = struct.unpack('<4I', data[:16])
        
        # Calculate offsets
        mcvt_offset = 16  # Heightmap starts after header
        mcly_offset = mcvt_offset + (145 * 4)  # After heightmap
        mcrf_offset = mcly_offset + (n_layers * 8)  # After layers
        mclq_offset = mcrf_offset + (n_doodad_refs * 4)  # After doodad refs
        
        # Parse heightmap (145 floats)
        heights = []
        if len(data) >= mcvt_offset + (145 * 4):
            heights_data = data[mcvt_offset:mcvt_offset + (145 * 4)]
            heights = list(struct.unpack('<145f', heights_data))
        
        # Parse layer info
        layers = []
        if len(data) >= mcly_offset + (n_layers * 8):
            layer_data = data[mcly_offset:mcly_offset + (n_layers * 8)]
            for i in range(n_layers):
                texture_id, layer_flags = struct.unpack('<2I', layer_data[i * 8:(i + 1) * 8])
                layers.append({
                    'texture_id': texture_id,
                    'flags': layer_flags,
                    'effect_id': 0  # Not present in Alpha
                })
        
        # Parse doodad refs
        doodad_refs = []
        if len(data) >= mcrf_offset + (n_doodad_refs * 4):
            refs_data = data[mcrf_offset:mcrf_offset + (n_doodad_refs * 4)]
            doodad_refs = list(struct.unpack(f'<{n_doodad_refs}I', refs_data))
        
        # Parse liquid data if present
        liquid_data = None
        if len(data) > mclq_offset:
            # Alpha liquid data format is simpler than retail
            liquid_data = data[mclq_offset:]
        
        return {
            'header': {
                'flags': flags,
                'area_id': area_id,
                'n_layers': n_layers,
                'n_doodad_refs': n_doodad_refs
            },
            'heights': heights,
            'layers': layers,
            'doodad_refs': doodad_refs,
            'liquid_data': liquid_data.hex() if liquid_data else None,
            'offsets': {
                'mcvt': mcvt_offset,
                'mcly': mcly_offset,
                'mcrf': mcrf_offset,
                'mclq': mclq_offset if liquid_data else 0
            }
        }

    def encode(self, data: Dict[str, Any]) -> bytes:
        result = bytearray()
        
        # Write header
        header = data['header']
        result.extend(struct.pack('<4I',
            header['flags'],
            header['area_id'],
            header['n_layers'],
            header['n_doodad_refs']
        ))
        
        # Write heightmap
        heights = data.get('heights', [])
        if heights:
            result.extend(struct.pack(f'<{len(heights)}f', *heights))
        
        # Write layers
        layers = data.get('layers', [])
        for layer in layers:
            result.extend(struct.pack('<2I',
                layer['texture_id'],
                layer['flags']
            ))
        
        # Write doodad refs
        doodad_refs = data.get('doodad_refs', [])
        if doodad_refs:
            result.extend(struct.pack(f'<{len(doodad_refs)}I', *doodad_refs))
        
        # Write liquid data
        liquid_data = data.get('liquid_data')
        if liquid_data:
            result.extend(bytes.fromhex(liquid_data))
        
        return bytes(result)

class AlphaMCLYDecoder(ChunkDecoder):
    """
    MCLY chunk decoder - Layer definitions (Alpha format)
    Simpler structure than retail format
    """
    def __init__(self):
        super().__init__(b'MCLY')

    def decode(self, data: bytes) -> Dict[str, Any]:
        layers = []
        pos = 0
        while pos + 8 <= len(data):
            texture_id, flags = struct.unpack('<2I', data[pos:pos+8])
            layers.append({
                'texture_id': texture_id,
                'flags': flags,
                'effect_id': 0  # Not present in Alpha
            })
            pos += 8
            
        return {
            'layers': layers,
            'layer_count': len(layers)
        }

    def encode(self, data: Dict[str, Any]) -> bytes:
        result = bytearray()
        for layer in data['layers']:
            result.extend(struct.pack('<2I',
                layer['texture_id'],
                layer['flags']
            ))
        return bytes(result)

class AlphaMCLQDecoder(ChunkDecoder):
    """
    MCLQ chunk decoder - Liquid data (Alpha format)
    Simpler structure than retail format
    """
    def __init__(self):
        super().__init__(b'MCLQ')

    def decode(self, data: bytes) -> Dict[str, Any]:
        # Alpha liquid data is just raw bytes
        return {
            'liquid_data': data.hex(),
            'size': len(data)
        }

    def encode(self, data: Dict[str, Any]) -> bytes:
        return bytes.fromhex(data['liquid_data'])