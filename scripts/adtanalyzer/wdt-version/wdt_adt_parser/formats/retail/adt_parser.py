"""
Retail format ADT parser implementation.
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

class RetailADTParser(ADTParser):
    """Parser for Retail format ADT files"""
    
    def __init__(self):
        """Initialize the Retail ADT parser"""
        super().__init__()
        self.db: Optional[DatabaseManager] = None
        self.wdt_id: Optional[int] = None
        self.chunk_order: List[str] = []
        self.texture_info: Dict[int, Dict[str, Any]] = {}
        self.x: int = -1
        self.y: int = -1
    
    def _setup_chunk_registry(self) -> None:
        """Register Retail-specific chunk parsers"""
        super()._setup_chunk_registry()
        self.chunk_registry.update({
            'MCNK': self._parse_mcnk,  # Map chunks
            'MTEX': self._parse_mtex,  # Texture names
            'MMDX': self._parse_mmdx,  # M2 model filenames
            'MMID': self._parse_mmid,  # M2 model indices
            'MWMO': self._parse_mwmo,  # WMO filenames
            'MWID': self._parse_mwid,  # WMO indices
        })
    
    def _parse_mcnk_subchunks(self, data: bytes, offsets: Dict[str, int],
                             n_layers: int) -> Dict[str, Any]:
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
            layer_size = 16  # Retail uses 16-byte layer entries
            mcly_size = n_layers * layer_size
            mcly_data = data[offsets['mcly']:offsets['mcly'] + mcly_size]
            
            layers = []
            for i in range(n_layers):
                texture_id, flags, mcal_offset, effect_id = struct.unpack('<4I', mcly_data[i * layer_size:(i + 1) * layer_size])
                layer = LayerInfo(
                    texture_id=texture_id,
                    flags=flags,
                    effect_id=effect_id,
                    blend_mode=(flags >> 24) & 0xFF
                )
                layers.append(layer)
                
                # Store in database if available
                if self.db and self.wdt_id:
                    self.db.insert_tile_layer(
                        self.wdt_id,
                        self.x, self.y,
                        texture_id,
                        flags,
                        mcal_offset
                    )
            
            result['layers'] = layers
        
        # Parse liquid data (MCLQ)
        if offsets['mclq'] > 0 and offsets.get('mclq_size', 0) > 0:
            mclq_data = data[offsets['mclq']:offsets['mclq'] + offsets['mclq_size']]
            if len(mclq_data) >= 8:
                liquid_type, flags = struct.unpack('<2I', mclq_data[:8])
                liquid_heights = []
                
                if len(mclq_data) > 8:
                    n_vertices = (len(mclq_data) - 8) // 4
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
                            flags
                        )
                
                result['liquid'] = LiquidInfo(
                    type=liquid_type,
                    heights=liquid_heights,
                    flags=flags
                )
        
        return result
    
    def _parse_mcnk(self, data: bytes) -> Dict[str, Any]:
        """Parse MCNK (Map Chunk) chunk"""
        if len(data) < 128:  # Retail MCNK header size
            raise ValueError(f"Invalid MCNK chunk size: {len(data)}")
        
        # Parse header
        header = struct.unpack('<8I2i2I2i2I2i2I', data[:64])
        flags = header[0]
        area_id = header[13]
        n_layers = header[2]
        n_doodad_refs = header[3]
        holes = header[12]
        
        # Get offsets
        offsets = {
            'mcvt': header[5],  # heightmap
            'mcnr': header[6],  # normals
            'mcly': header[7],  # layers
            'mcrf': header[8],  # refs
            'mcal': header[9],  # alpha maps
            'mcsh': header[10], # shadows
            'mcal_size': header[11],
            'mclq': header[14], # liquid
            'mclq_size': header[15]
        }
        
        # Parse sub-chunks
        subchunk_data = self._parse_mcnk_subchunks(data, offsets, n_layers)
        
        # Create MCNKInfo
        mcnk = MCNKInfo(
            flags=flags,
            area_id=area_id,
            n_layers=n_layers,
            n_doodad_refs=n_doodad_refs,
            holes=holes,
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
                holes
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
                    0,  # blend_mode
                    False,  # has_alpha
                    False,  # is_compressed
                    0,  # effect_id
                    0  # flags
                )
        
        return {'textures': textures}
    
    def _parse_mmdx(self, data: bytes) -> Dict[str, Any]:
        """Parse MMDX (M2 Model Filenames) chunk"""
        names = data.split(b'\0')
        models = [name.decode('utf-8', 'ignore') for name in names if name]
        return {'models': models}
    
    def _parse_mmid(self, data: bytes) -> Dict[str, Any]:
        """Parse MMID (M2 Model Indices) chunk"""
        count = len(data) // 4
        indices = struct.unpack(f'<{count}I', data)
        return {'indices': list(indices)}
    
    def _parse_mwmo(self, data: bytes) -> Dict[str, Any]:
        """Parse MWMO (WMO Filenames) chunk"""
        names = data.split(b'\0')
        models = [name.decode('utf-8', 'ignore') for name in names if name]
        return {'models': models}
    
    def _parse_mwid(self, data: bytes) -> Dict[str, Any]:
        """Parse MWID (WMO Indices) chunk"""
        count = len(data) // 4
        indices = struct.unpack(f'<{count}I', data)
        return {'indices': list(indices)}
    
    def parse(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Parse ADT file
        
        Args:
            file_path: Path to ADT file
            
        Returns:
            Dictionary containing parsed ADT data
        """
        self.open(file_path)
        
        result = {
            'format': 'retail',
            'version': None,
            'chunks': [],
            'errors': []
        }
        
        try:
            # Process all chunks
            for header, chunk_data in self.iterate_chunks():
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
            result['errors'].append(f"Error parsing ADT file: {e}")
        
        return result
    
    def parse_embedded_data(self, data: bytes, x: int, y: int) -> Dict[str, Any]:
        """
        Parse embedded ADT data from WDT file
        Not used in Retail format
        """
        raise NotImplementedError("Retail format does not use embedded ADT data")