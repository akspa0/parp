"""
Retail format ADT parser implementation.
"""
from typing import Dict, Any, List, Optional, Tuple
import struct
import logging
from pathlib import Path
import array

from wdt_adt_parser.base.adt_parser import ADTParser, MCNKInfo, LayerInfo, HeightmapInfo, LiquidInfo

class RetailADTParser(ADTParser):
    """Parser for Retail format ADT files"""
    
    def __init__(self):
        """Initialize the Retail ADT parser"""
        super().__init__()
        self.db: Optional[DatabaseManager] = None
        self.wdt_id: Optional[int] = None
        self.x: int = -1
        self.y: int = -1
        self.chunk_order: List[str] = []
        self.texture_info: Dict[int, Dict[str, Any]] = {}
    
    def _setup_chunk_registry(self) -> None:
        """Register Retail-specific chunk parsers"""
        super()._setup_chunk_registry()
        self.chunk_registry.update({
            'MCVT': self._parse_mcvt,  # Height map
            'MCNR': self._parse_mcnr,  # Normals
            'MCLY': self._parse_mcly,  # Texture layers
            'MCAL': self._parse_mcal,  # Alpha maps
            'MCLQ': self._parse_mclq,  # Old liquid
            'MH2O': self._parse_mh2o,  # New liquid
            'MCRF': self._parse_mcrf,  # Doodad references
            'MCSH': self._parse_mcsh,  # Shadow map
            'MCCV': self._parse_mccv,  # Vertex colors
        })
    
    def _parse_mcvt(self, data: bytes) -> Dict[str, Any]:
        """
        Parse MCVT (Height Map) chunk
        Retail format uses a 145-point height map (9x9 + 8x8 grid)
        """
        if len(data) != 145 * 4:  # 145 float values
            raise ValueError(f"Invalid MCVT chunk size: {len(data)}")
        
        heights = array.array('f')
        heights.frombytes(data)
        heights_list = list(heights)
        
        # Store in database if available
        if self.db and self.wdt_id:
            self.db.insert_height_map(
                self.wdt_id,
                self.x, self.y,
                heights_list
            )
        
        return {
            'heights': heights_list,
            'grid_size': (9, 9)
        }
    
    def _parse_mcnr(self, data: bytes) -> Dict[str, Any]:
        """Parse MCNR (Normal Map) chunk"""
        if len(data) < 145 * 3:  # 145 normals * 3 bytes each
            raise ValueError(f"Invalid MCNR chunk size: {len(data)}")
        
        normals = []
        for i in range(145):
            offset = i * 3
            x, y, z = struct.unpack('3B', data[offset:offset + 3])
            normals.append({
                'x': (x - 127) / 127,
                'y': (y - 127) / 127,
                'z': (z - 127) / 127
            })
        
        return {'normals': normals}
    
    def _parse_mcly(self, data: bytes) -> Dict[str, Any]:
        """
        Parse MCLY (Texture Layers) chunk
        Retail format uses 16 bytes per layer:
        - texture_id (uint32)
        - flags (uint32)
        - offset_in_mcal (uint32)
        - effect_id (uint32)
        """
        if len(data) % 16 != 0:
            raise ValueError(f"Invalid MCLY chunk size: {len(data)}")
        
        layer_count = len(data) // 16
        layers = []
        
        for i in range(layer_count):
            offset = i * 16
            texture_id, flags, mcal_offset, effect_id = struct.unpack('<4I', data[offset:offset + 16])
            
            layer = LayerInfo(
                texture_id=texture_id,
                flags=flags,
                effect_id=effect_id,
                blend_mode=(flags >> 24) & 0x7
            )
            layers.append(layer)
            
            # Store in database if available
            if self.db and self.wdt_id:
                self.db.insert_tile_layer(
                    self.wdt_id,
                    self.x, self.y,
                    texture_id,
                    flags,
                    mcal_offset  # Retail format uses MCAL offsets
                )
        
        return {'layers': layers}
    
    def _parse_mcal(self, data: bytes) -> Dict[str, Any]:
        """Parse MCAL (Alpha Map) chunk"""
        # Each alpha map is 4096 bytes (64x64)
        alpha_maps = []
        offset = 0
        
        while offset + 4096 <= len(data):
            alpha_map = array.array('B')
            alpha_map.frombytes(data[offset:offset + 4096])
            alpha_maps.append(list(alpha_map))
            offset += 4096
        
        return {'alpha_maps': alpha_maps}
    
    def _parse_mclq(self, data: bytes) -> Dict[str, Any]:
        """Parse MCLQ (Old Liquid) chunk"""
        if len(data) < 8:
            raise ValueError(f"Invalid MCLQ chunk size: {len(data)}")
        
        liquid_type, liquid_flags = struct.unpack('<2I', data[:8])
        
        # Parse height map if present
        heights = []
        if len(data) > 8:
            height_data = data[8:]
            height_count = len(height_data) // 4
            heights = array.array('f')
            heights.frombytes(height_data[:height_count * 4])
        
        heights_list = list(heights) if heights else None
        min_height = min(heights_list) if heights_list else None
        max_height = max(heights_list) if heights_list else None
        
        # Store in database if available
        if self.db and self.wdt_id:
            self.db.insert_liquid_data(
                self.wdt_id,
                self.x, self.y,
                liquid_type,
                heights_list,
                liquid_flags,
                min_height,
                max_height
            )
        
        return {
            'type': liquid_type,
            'flags': liquid_flags,
            'heights': heights_list
        }
    
    def _parse_mh2o(self, data: bytes) -> Dict[str, Any]:
        """Parse MH2O (New Liquid) chunk"""
        if len(data) < 30:  # Minimum header size
            raise ValueError(f"Invalid MH2O chunk size: {len(data)}")
        
        # Parse header
        info_mask, height_min, height_max, x_offset, y_offset, width, height = struct.unpack('<IBBHHHH', data[:14])
        
        # Parse liquid vertices if present
        vertices = []
        if width > 0 and height > 0:
            vertex_count = width * height
            vertex_data = data[14:14 + vertex_count * 8]  # 8 bytes per vertex
            for i in range(vertex_count):
                offset = i * 8
                height, depth = struct.unpack('<2f', vertex_data[offset:offset + 8])
                vertices.append({'height': height, 'depth': depth})
        
        # Extract heights from vertices
        heights_list = [v['height'] for v in vertices] if vertices else None
        
        # Store in database if available
        if self.db and self.wdt_id:
            self.db.insert_liquid_data(
                self.wdt_id,
                self.x, self.y,
                info_mask & 0x1F,  # liquid type is in lower 5 bits
                heights_list,
                info_mask,  # store full info mask as flags
                height_min,
                height_max
            )
        
        return {
            'info_mask': info_mask,
            'height_range': {'min': height_min, 'max': height_max},
            'position': {'x': x_offset, 'y': y_offset},
            'size': {'width': width, 'height': height},
            'vertices': vertices
        }
    
    def _parse_mcrf(self, data: bytes) -> Dict[str, Any]:
        """Parse MCRF (Doodad References) chunk"""
        if len(data) % 4 != 0:
            raise ValueError(f"Invalid MCRF chunk size: {len(data)}")
        
        ref_count = len(data) // 4
        refs = struct.unpack(f'<{ref_count}I', data)
        
        return {'doodad_refs': list(refs)}
    
    def _parse_mcsh(self, data: bytes) -> Dict[str, Any]:
        """Parse MCSH (Shadow Map) chunk"""
        if len(data) != 64 * 64:  # 64x64 shadow map
            raise ValueError(f"Invalid MCSH chunk size: {len(data)}")
        
        shadow_map = array.array('B')
        shadow_map.frombytes(data)
        
        return {'shadow_map': list(shadow_map)}
    
    def _parse_mccv(self, data: bytes) -> Dict[str, Any]:
        """Parse MCCV (Vertex Colors) chunk"""
        if len(data) != 145 * 4:  # 145 vertices * 4 bytes (BGRA)
            raise ValueError(f"Invalid MCCV chunk size: {len(data)}")
        
        colors = []
        for i in range(145):
            offset = i * 4
            b, g, r, a = struct.unpack('4B', data[offset:offset + 4])
            colors.append({'r': r, 'g': g, 'b': b, 'a': a})
        
        return {'vertex_colors': colors}
    
    def _parse_mcnk(self, data: bytes) -> Dict[str, Any]:
        """
        Parse Retail MCNK chunk header
        Retail format has a 128-byte header
        """
        if len(data) < 128:
            raise ValueError(f"Invalid Retail MCNK header size: {len(data)}")
        
        # Parse header fields
        flags = struct.unpack('<I', data[0:4])[0]
        idx_x = struct.unpack('<I', data[4:8])[0]
        idx_y = struct.unpack('<I', data[8:12])[0]
        n_layers = struct.unpack('<I', data[12:16])[0]
        n_doodad_refs = struct.unpack('<I', data[16:20])[0]
        
        # Get offsets to subchunks
        offsets = {
            'mcvt': struct.unpack('<I', data[20:24])[0],   # Height map
            'mcnr': struct.unpack('<I', data[24:28])[0],   # Normals
            'mcly': struct.unpack('<I', data[28:32])[0],   # Layers
            'mcrf': struct.unpack('<I', data[32:36])[0],   # Refs
            'mcal': struct.unpack('<I', data[36:40])[0],   # Alpha maps
            'mcsh': struct.unpack('<I', data[40:44])[0],   # Shadows
            'mcal_size': struct.unpack('<I', data[44:48])[0],
            'mclq': struct.unpack('<I', data[48:52])[0],   # Liquid
            'mclq_size': struct.unpack('<I', data[52:56])[0],
            'mccv': struct.unpack('<I', data[56:60])[0],   # Vertex colors
            'mclv': struct.unpack('<I', data[60:64])[0],   # ???
            'unused': struct.unpack('<16I', data[64:128])  # Reserved
        }
        
        return {
            'flags': flags,
            'position': {'x': idx_x, 'y': idx_y},
            'layer_count': n_layers,
            'doodad_refs': n_doodad_refs,
            'offsets': offsets
        }
    
    def parse(self) -> Dict[str, Any]:
        """
        Parse Retail format ADT file
        
        Returns:
            Dictionary containing parsed ADT data
        """
        result = {
            'format': 'retail',
            'version': None,
            'chunks': [],
            'textures': [],
            'errors': []
        }
        
        try:
            # First pass: Process version and textures
            for header, data in self.iterate_chunks():
                try:
                    if header.name == 'MVER':
                        result.update(self.parse_chunk(header, data))
                    elif header.name == 'MTEX':
                        mtex_data = self.parse_chunk(header, data)
                        result['textures'] = mtex_data['textures']
                except Exception as e:
                    result['errors'].append(f"Error parsing {header.name} chunk: {e}")
            
            # Second pass: Process MCNK chunks and their subchunks
            current_chunk = None
            for header, data in self.iterate_chunks():
                try:
                    if header.name == 'MCNK':
                        chunk_data = self.parse_chunk(header, data)
                        current_chunk = chunk_data
                        result['chunks'].append(chunk_data)
                    elif current_chunk and header.name in ['MCVT', 'MCNR', 'MCLY', 'MCAL', 'MCLQ', 'MH2O', 'MCRF', 'MCSH', 'MCCV']:
                        # Process sub-chunks under current MCNK
                        sub_data = self.parse_chunk(header, data)
                        current_chunk[header.name.lower()] = sub_data
                except Exception as e:
                    result['errors'].append(f"Error parsing {header.name} chunk: {e}")
            
        except Exception as e:
            result['errors'].append(f"Error parsing ADT file: {e}")
        
        return result
    
    def get_heightmap(self, chunk_x: int, chunk_y: int) -> Optional[HeightmapInfo]:
        """Get heightmap data for a specific chunk"""
        chunk = self.get_chunk(chunk_x, chunk_y)
        if not chunk or 'mcvt' not in chunk:
            return None
            
        return HeightmapInfo(
            heights=chunk['mcvt']['heights'],
            holes=chunk['flags'] & 0x10000  # Check hole flag
        )
    
    def get_texture_layers(self, chunk_x: int, chunk_y: int) -> List[LayerInfo]:
        """Get texture layers for a specific chunk"""
        chunk = self.get_chunk(chunk_x, chunk_y)
        if not chunk or 'mcly' not in chunk:
            return []
            
        return chunk['mcly']['layers']
    
    def get_liquid_data(self, chunk_x: int, chunk_y: int) -> Optional[LiquidInfo]:
        """Get liquid data for a specific chunk"""
        chunk = self.get_chunk(chunk_x, chunk_y)
        if not chunk:
            return None
            
        # Try new liquid format first (MH2O)
        if 'mh2o' in chunk:
            liquid = chunk['mh2o']
            return LiquidInfo(
                type=liquid['info_mask'] & 0x1F,
                height_map=[v['height'] for v in liquid['vertices']],
                flags=liquid['info_mask'],
                min_height=liquid['height_range']['min'],
                max_height=liquid['height_range']['max']
            )
        # Fall back to old liquid format (MCLQ)
        elif 'mclq' in chunk:
            liquid = chunk['mclq']
            return LiquidInfo(
                type=liquid['type'],
                height_map=liquid['heights'] if liquid['heights'] else [],
                flags=liquid['flags'],
                min_height=min(liquid['heights']) if liquid['heights'] else 0.0,
                max_height=max(liquid['heights']) if liquid['heights'] else 0.0
            )
            
        return None