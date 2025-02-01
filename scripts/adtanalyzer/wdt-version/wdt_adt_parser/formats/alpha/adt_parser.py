"""
Alpha format ADT parser implementation.
"""
from typing import Dict, Any, List, Optional, Union
import struct
import array
import logging
from pathlib import Path

from wdt_adt_parser.base.adt_parser import (
    ADTParser, MCNKInfo, LayerInfo, HeightmapInfo, LiquidInfo
)
from wdt_adt_parser.database import DatabaseManager

class AlphaADTParser(ADTParser):
    """Parser for Alpha format ADT data"""
    
    def __init__(self):
        """Initialize the Alpha ADT parser"""
        super().__init__()
        self.db: Optional[DatabaseManager] = None
        self.wdt_id: Optional[int] = None
        self.chunk_order: List[str] = []
        self.texture_info: Dict[int, Dict[str, Any]] = {}
        self.x: int = -1
        self.y: int = -1
    
    def _setup_chunk_registry(self) -> None:
        """Register Alpha-specific chunk parsers"""
        super()._setup_chunk_registry()
        self.chunk_registry.update({
            'MCNK': self._parse_mcnk,  # Map chunks (Alpha format specific)
            'MTEX': self._parse_mtex,  # Texture names
        })
    
    def _parse_mcnk_subchunks(self, data: bytes, offsets: Dict[str, int],
                             n_layers: int, n_doodad_refs: int) -> Dict[str, Any]:
        """Parse MCNK sub-chunks"""
        result = {}
        
        # Parse heightmap (MCVT)
        if offsets['mcvt'] > 0:
            mcvt_size = 145 * 4  # 145 floats
            mcvt_data = data[offsets['mcvt']:offsets['mcvt'] + mcvt_size]
            heights = array.array('f')
            heights.frombytes(mcvt_data)
            heights_list = list(heights)
            
            result['heightmap'] = HeightmapInfo(
                heights=heights_list,
                min_height=min(heights_list),
                max_height=max(heights_list)
            )
            
            # Store in database if available
            if self.db and self.wdt_id:
                self.db.insert_height_map(
                    self.wdt_id,
                    self.x, self.y,
                    heights_list
                )
        
        # Parse layers (MCLY)
        if offsets['mcly'] > 0 and n_layers > 0:
            layer_size = 8  # Alpha uses 8-byte layer entries
            mcly_size = n_layers * layer_size
            mcly_data = data[offsets['mcly']:offsets['mcly'] + mcly_size]
            
            layers = []
            for i in range(n_layers):
                texture_id, layer_flags = struct.unpack('<2I', mcly_data[i * layer_size:(i + 1) * layer_size])
                layer = LayerInfo(
                    texture_id=texture_id,
                    flags=layer_flags,
                    effect_id=0,  # Not present in Alpha
                    blend_mode=0   # Not present in Alpha
                )
                layers.append(layer)
                
                # Store in database if available
                if self.db and self.wdt_id:
                    self.db.insert_tile_layer(
                        self.wdt_id,
                        self.x, self.y,
                        texture_id,
                        layer_flags,
                        0  # Alpha format doesn't use MCAL offsets
                    )
            
            result['layers'] = layers
        
        # Parse liquid data (MCLQ)
        if offsets['mclq'] > 0:
            mclq_data = data[offsets['mclq']:]
            if len(mclq_data) >= 8:
                liquid_type, n_vertices = struct.unpack('<2I', mclq_data[:8])
                liquid_heights = []
                
                if n_vertices > 0 and len(mclq_data) >= 8 + (n_vertices * 4):
                    heights = array.array('f')
                    heights.frombytes(mclq_data[8:8 + (n_vertices * 4)])
                    liquid_heights = list(heights)
                    
                    # Store in database if available
                    if self.db and self.wdt_id:
                        self.db.insert_liquid_data(
                            self.wdt_id,
                            self.x, self.y,
                            liquid_type,
                            liquid_heights,
                            0  # flags not used in Alpha
                        )
                
                result['liquid'] = LiquidInfo(
                    type=liquid_type,
                    heights=liquid_heights,
                    flags=0  # Not used in Alpha
                )
        
        return result
    
    def _parse_mcnk(self, data: bytes) -> Dict[str, Any]:
        """
        Parse Alpha-specific MCNK chunk (Map Chunk)
        Reference: https://wowdev.wiki/Alpha#MCNK
        
        Alpha MCNK has a simplified 16-byte header followed by:
        - MCVT: 145 float values (9x9 + 8x8 grid) for heightmap
        - MCLY: n_layers * 8 bytes for layer info
        - MCRF: n_doodad_refs * 4 bytes for doodad references
        - MCLQ: Liquid data (if present)
        """
        if len(data) < 16:  # Minimum header size for Alpha MCNK
            raise ValueError(f"Invalid Alpha MCNK chunk size: {len(data)}")
        
        # Parse header exactly as in original code
        flags, area_id, n_layers, n_doodad_refs = struct.unpack('<4I', data[:16])
        
        # Calculate offsets
        mcvt_offset = 16  # Heightmap starts after header
        mcly_offset = mcvt_offset + (145 * 4)  # After heightmap
        mcrf_offset = mcly_offset + (n_layers * 8)  # After layers
        mclq_offset = mcrf_offset + (n_doodad_refs * 4)  # After doodad refs
        
        offsets = {
            'mcvt': mcvt_offset,
            'mcly': mcly_offset,
            'mcrf': mcrf_offset,
            'mclq': mclq_offset
        }
        
        # Parse sub-chunks
        subchunk_data = self._parse_mcnk_subchunks(data, offsets, n_layers, n_doodad_refs)
        
        # Create MCNKInfo
        mcnk = MCNKInfo(
            flags=flags,
            area_id=area_id,
            n_layers=n_layers,
            n_doodad_refs=n_doodad_refs,
            holes=0,  # Not used in Alpha
            heightmap=subchunk_data.get('heightmap'),
            layers=subchunk_data.get('layers', []),
            liquid=subchunk_data.get('liquid'),
            offsets=offsets
        )
        
        # Store MCNK info in database if available
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
        
        # Add to list of MCNK chunks
        self.mcnk_chunks.append(mcnk)
        
        return {'mcnk': mcnk}
    
    def _parse_mtex(self, data: bytes) -> Dict[str, Any]:
        """Parse MTEX (Map Textures) chunk"""
        names = data.split(b'\0')
        textures = [name.decode('utf-8', 'ignore') for name in names if name]
        
        # Store textures
        self.textures.extend(textures)
        
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
    
    def parse(self, file_path: Union[str, Path]) -> Dict[str, Any]:
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
            # First pass: Process MTEX chunk to get texture information
            for header, chunk_data in self.iterate_chunks(data):
                if header.name == 'MTEX':
                    try:
                        mtex_result = self.parse_chunk(header, chunk_data)
                        result['textures'] = mtex_result['textures']
                        break
                    except Exception as e:
                        result['errors'].append(f"Error parsing MTEX chunk: {e}")
            
            # Second pass: Process remaining chunks
            for header, chunk_data in self.iterate_chunks(data):
                if header.name != 'MTEX':  # Skip MTEX as we've already processed it
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