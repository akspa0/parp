"""
Alpha format ADT parser implementation.
"""
from typing import Dict, Any, List, Optional
import struct
import logging
from pathlib import Path

from wdt_adt_parser.base.adt_parser import ADTParser
from wdt_adt_parser.database import DatabaseManager

class AlphaADTParser(ADTParser):
    """Parser for Alpha format ADT data"""
    
    def __init__(self):
        """Initialize the Alpha ADT parser"""
        super().__init__()
        self.db: Optional[DatabaseManager] = None
        self.wdt_id: Optional[int] = None
        self.x: int = -1
        self.y: int = -1
        self.chunk_order: List[str] = []
        self.texture_info: Dict[int, Dict[str, Any]] = {}
    
    def _setup_chunk_registry(self) -> None:
        """Register Alpha-specific chunk parsers"""
        super()._setup_chunk_registry()
        self.chunk_registry.update({
            'MCNK': self._parse_mcnk,  # Map chunks (Alpha format specific)
            'MTEX': self._parse_mtex,  # Texture names
            'MCVT': self._parse_mcvt,  # Height map
            'MCLY': self._parse_mcly,  # Texture layers
            'MCLQ': self._parse_mclq,  # Liquid data
            'MCSH': self._parse_mcsh,  # Shadow map
            'MCCV': self._parse_mccv,  # Vertex colors
        })
    
    def _parse_mtex(self, data: bytes) -> Dict[str, Any]:
        """Parse MTEX (Map Textures) chunk"""
        names = data.split(b'\0')
        textures = [name.decode('utf-8', 'ignore') for name in names if name]
        
        # Store texture info for later use
        for i, tex_path in enumerate(textures):
            self.texture_info[i] = {
                'path': tex_path,
                'flags': {'has_alpha': False, 'is_terrain': True},
                'layer_index': i
            }
            
            # Store in database if available
            if self.db and self.wdt_id:
                self.db.insert_texture(
                    self.wdt_id,
                    self.x, self.y,
                    tex_path,
                    i,  # layer_index
                    0,  # blend_mode (not used in Alpha)
                    False,  # has_alpha
                    False,  # is_compressed
                    0,  # effect_id (not used in Alpha)
                    0  # flags
                )
        
        return {'textures': textures}
    
    def _parse_mcvt(self, data: bytes) -> Dict[str, Any]:
        """Parse MCVT (Map Chunk Vertex Table) chunk"""
        if len(data) < 145 * 4:  # 145 height values
            raise ValueError(f"Invalid MCVT chunk size: {len(data)}")
        
        heights = []
        for i in range(145):
            height = struct.unpack('<f', data[i * 4:(i + 1) * 4])[0]
            heights.append(height)
        
        # Store in database if available
        if self.db and self.wdt_id:
            self.db.insert_height_map(self.wdt_id, self.x, self.y, heights)
        
        return {'heights': heights}
    
    def _parse_mcly(self, data: bytes) -> Dict[str, Any]:
        """Parse MCLY (Map Chunk Layer) chunk"""
        if len(data) < 8:  # At least one layer entry
            raise ValueError(f"Invalid MCLY chunk size: {len(data)}")
        
        layers = []
        n_layers = len(data) // 8  # Each layer is 8 bytes
        
        for i in range(n_layers):
            texture_id, flags = struct.unpack('<2I', data[i * 8:(i + 1) * 8])
            layer = {
                'texture_id': texture_id,
                'flags': flags,
                'flags_decoded': {
                    'use_alpha_map': bool(flags & 0x1),
                    'alpha_compressed': bool(flags & 0x2),
                    'use_height_texture': bool(flags & 0x4)
                }
            }
            layers.append(layer)
            
            # Store in database if available
            if self.db and self.wdt_id:
                self.db.insert_tile_layer(
                    self.wdt_id,
                    self.x, self.y,
                    texture_id,
                    flags,
                    0  # Alpha format doesn't use MCAL offsets
                )
        
        return {'layers': layers}

    def _parse_mclq(self, data: bytes) -> Dict[str, Any]:
        """Parse MCLQ (Map Chunk Liquid) chunk"""
        if len(data) < 8:  # Minimum header size
            raise ValueError(f"Invalid MCLQ chunk size: {len(data)}")
        
        # Parse liquid header
        type_id, n_vertices = struct.unpack('<2I', data[:8])
        
        # Parse liquid heights if present
        heights = []
        if n_vertices > 0 and len(data) >= 8 + (n_vertices * 4):
            for i in range(n_vertices):
                height = struct.unpack('<f', data[8 + i * 4:12 + i * 4])[0]
                heights.append(height)
        
        # Calculate min/max heights
        min_height = min(heights) if heights else None
        max_height = max(heights) if heights else None
        
        # Store in database if available
        if self.db and self.wdt_id:
            self.db.insert_liquid_data(
                self.wdt_id,
                self.x, self.y,
                type_id,
                heights,
                0,  # flags (not used in Alpha)
                min_height,
                max_height
            )
        
        return {
            'type': type_id,
            'n_vertices': n_vertices,
            'heights': heights,
            'min_height': min_height,
            'max_height': max_height
        }

    def _parse_mcsh(self, data: bytes) -> Dict[str, Any]:
        """Parse MCSH (Map Chunk Shadow) chunk"""
        if len(data) < 64:  # 8x8 shadow map
            raise ValueError(f"Invalid MCSH chunk size: {len(data)}")
        
        # In Alpha format, shadow data is a simple 8x8 grid of bytes
        shadow_map = []
        for i in range(64):
            value = data[i]
            shadow_map.append(value)
        
        return {'shadow_map': shadow_map}

    def _parse_mccv(self, data: bytes) -> Dict[str, Any]:
        """Parse MCCV (Map Chunk Vertex Colors) chunk"""
        if len(data) < 145 * 4:  # RGBA for each vertex
            raise ValueError(f"Invalid MCCV chunk size: {len(data)}")
        
        vertex_colors = []
        for i in range(145):  # 145 vertices per chunk
            offset = i * 4
            r, g, b, a = struct.unpack('4B', data[offset:offset + 4])
            vertex_colors.append({
                'r': r,
                'g': g,
                'b': b,
                'a': a
            })
        
        return {'vertex_colors': vertex_colors}
    
    def _parse_mcnk(self, data: bytes) -> Dict[str, Any]:
        """
        Parse MCNK (Map Chunk) chunk
        In Alpha format, MCNK chunks contain simplified terrain data
        """
        if len(data) < 16:  # Minimum header size for Alpha MCNK
            raise ValueError(f"Invalid Alpha MCNK chunk size: {len(data)}")
        
        # Parse header
        flags, area_id, n_layers, n_doodad_refs = struct.unpack('<4I', data[:16])
        
        # Calculate offsets
        mcvt_offset = 16  # Heightmap starts after header
        mcly_offset = mcvt_offset + (145 * 4)  # After heightmap
        mcrf_offset = mcly_offset + (n_layers * 8)  # After layers
        mcsh_offset = mcrf_offset + (n_doodad_refs * 4)  # After doodad refs
        mccv_offset = mcsh_offset + 64  # After shadow map (8x8 grid)
        mclq_offset = mccv_offset + (145 * 4)  # After vertex colors
        
        result = {
            'flags': flags,
            'area_id': area_id,
            'n_layers': n_layers,
            'n_doodad_refs': n_doodad_refs,
            'offsets': {
                'mcvt': mcvt_offset,
                'mcly': mcly_offset,
                'mcrf': mcrf_offset,
                'mcsh': mcsh_offset,
                'mccv': mccv_offset,
                'mclq': mclq_offset
            }
        }
        
        # Store in database if available
        if self.db and self.wdt_id:
            self.db.insert_tile_mcnk(
                self.wdt_id,
                self.x, self.y,
                flags,
                area_id,
                n_layers,
                n_doodad_refs,
                0  # holes not used in Alpha
            )
            
            # Parse and store heightmap data
            if len(data) >= mcvt_offset + (145 * 4):
                mcvt_data = data[mcvt_offset:mcvt_offset + (145 * 4)]
                self._parse_mcvt(mcvt_data)
            
            # Parse and store layer data
            if len(data) >= mcly_offset + (n_layers * 8):
                mcly_data = data[mcly_offset:mcly_offset + (n_layers * 8)]
                self._parse_mcly(mcly_data)
            
            # Parse and store shadow map data
            if len(data) >= mcsh_offset + 64:  # 8x8 shadow map
                mcsh_data = data[mcsh_offset:mcsh_offset + 64]
                self._parse_mcsh(mcsh_data)
            
            # Parse and store vertex colors
            if len(data) >= mccv_offset + (145 * 4):  # RGBA for each vertex
                mccv_data = data[mccv_offset:mccv_offset + (145 * 4)]
                self._parse_mccv(mccv_data)
            
            # Parse and store liquid data if present
            if len(data) >= mclq_offset + 8:  # At least header size
                mclq_data = data[mclq_offset:]  # Take all remaining data
                try:
                    self._parse_mclq(mclq_data)
                except Exception as e:
                    self.logger.warning(f"Failed to parse MCLQ data: {e}")
        
        return result
    
    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Parse ADT file (not used in Alpha format)
        
        Args:
            file_path: Path to ADT file
            
        Returns:
            Dictionary containing parsed ADT data
        """
        raise NotImplementedError("Alpha format does not use separate ADT files")
    
    def parse_embedded_data(self, data: bytes, x: int, y: int) -> Dict[str, Any]:
        """
        Parse embedded ADT data from WDT file
        
        Args:
            data: Raw ADT data from WDT file
            x: X coordinate of tile
            y: Y coordinate of tile
            
        Returns:
            Dictionary containing parsed ADT data
        """
        self.x = x
        self.y = y
        
        result = {
            'format': 'alpha',
            'coordinates': {'x': x, 'y': y},
            'chunks': [],
            'errors': []
        }
        
        try:
            # Process chunks in order
            for header, chunk_data in self.iterate_chunks(data):
                try:
                    # Track chunk order
                    self.chunk_order.append(header.name)
                    
                    # Store chunk offset in database
                    if self.db and self.wdt_id:
                        self.db.insert_chunk_offset(
                            self.wdt_id,
                            header.name,
                            header.offset,
                            header.size,
                            header.data_offset
                        )
                    
                    # Parse chunk
                    chunk_result = self.parse_chunk(header, chunk_data)
                    result['chunks'].append({
                        'name': header.name,
                        'data': chunk_result
                    })
                    
                except Exception as e:
                    result['errors'].append(f"Error parsing {header.name} chunk: {e}")
            
            # Add chunk order to result
            result['chunk_order'] = ','.join(self.chunk_order)
            
        except Exception as e:
            result['errors'].append(f"Error parsing ADT data: {e}")
        
        return result