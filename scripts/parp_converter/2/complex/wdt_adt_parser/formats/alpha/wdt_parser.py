"""
Alpha format WDT parser implementation.
"""
from typing import Dict, Any, List, Tuple, Optional
import struct
import logging
from pathlib import Path

from wdt_adt_parser.base.wdt_parser import WDTParser, MapTile, ModelPlacement
from wdt_adt_parser.database import DatabaseManager
from wdt_adt_parser.formats.alpha.adt_parser import AlphaADTParser

class AlphaWDTParser(WDTParser):
    """Parser for Alpha format WDT files"""
    
    def __init__(self):
        """Initialize the Alpha WDT parser"""
        super().__init__()
        self.db: Optional[DatabaseManager] = None
        self.wdt_id: Optional[int] = None
        self.chunk_order: List[str] = []
        self.texture_info: Dict[int, Dict[str, Any]] = {}
        self.adt_parser = AlphaADTParser()
    
    def _setup_chunk_registry(self) -> None:
        """Register Alpha-specific chunk parsers"""
        super()._setup_chunk_registry()
        self.chunk_registry.update({
            'MDNM': self._parse_mdnm,  # M2 model names
            'MONM': self._parse_monm,  # WMO model names
            'MCNK': self._parse_mcnk,  # Map chunks (Alpha format specific)
            'MAIN': self._parse_main,  # Map tile table
            'MTEX': self._parse_mtex,  # Texture names
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
                    -1, -1,  # Will be updated when processing MCNK
                    tex_path,
                    i,  # layer_index
                    0,  # blend_mode (not used in Alpha)
                    False,  # has_alpha
                    False,  # is_compressed
                    0,  # effect_id (not used in Alpha)
                    0  # flags
                )
        
        return {'textures': textures}
    
    def _parse_mdnm(self, data: bytes) -> Dict[str, Any]:
        """Parse MDNM (Map Doodad Name) chunk"""
        names = data.split(b'\0')
        self.m2_models = [name.decode('utf-8', 'ignore') for name in names if name]
        
        # Store in database if available
        if self.db and self.wdt_id:
            for model_path in self.m2_models:
                self.db.insert_m2_model(self.wdt_id, -1, -1, model_path, 'alpha')
        
        return {'names': self.m2_models}
    
    def _parse_monm(self, data: bytes) -> Dict[str, Any]:
        """Parse MONM (Map Object Name) chunk"""
        names = data.split(b'\0')
        self.wmo_models = [name.decode('utf-8', 'ignore') for name in names if name]
        
        # Store in database if available
        if self.db and self.wdt_id:
            for model_path in self.wmo_models:
                self.db.insert_wmo_model(self.wdt_id, -1, -1, model_path, 'alpha')
        
        return {'names': self.wmo_models}
    
    def _parse_mcnk(self, data: bytes) -> Dict[str, Any]:
        """
        Parse Alpha-specific MCNK chunk
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
        
        result = {
            'flags': flags,
            'area_id': area_id,
            'n_layers': n_layers,
            'n_doodad_refs': n_doodad_refs,
            'offsets': {
                'mcvt': mcvt_offset,
                'mcly': mcly_offset,
                'mcrf': mcrf_offset
            }
        }
        
        # Store in database if available
        if self.db and self.wdt_id:
            self.db.insert_tile_mcnk(
                self.wdt_id, -1, -1,  # TODO: Get proper coordinates
                flags, area_id, n_layers, n_doodad_refs, 0  # holes not used in Alpha
            )
            
            # Parse and store heightmap data
            if len(data) >= mcvt_offset + (145 * 4):
                heights = []
                for i in range(145):
                    height = struct.unpack('<f', data[mcvt_offset + i * 4:mcvt_offset + (i + 1) * 4])[0]
                    heights.append(height)
                self.db.insert_height_map(self.wdt_id, -1, -1, heights)
            
            # Parse and store layer data
            if len(data) >= mcly_offset + (n_layers * 8):
                layer_data = data[mcly_offset:mcly_offset + (n_layers * 8)]
                for i in range(n_layers):
                    texture_id, flags = struct.unpack('<2I', layer_data[i * 8:(i + 1) * 8])
                    self.db.insert_tile_layer(
                        self.wdt_id, -1, -1,
                        texture_id, flags, 0  # Alpha format doesn't use MCAL offsets
                    )
        
        return result
    
    def _parse_main(self, data: bytes) -> Dict[str, Any]:
        """
        Parse MAIN chunk (Map tile table)
        
        The MAIN chunk contains a 64x64 array of MapFileDataIDs.
        Each entry is 16 bytes:
        - offset (uint32): Offset to the ADT file in the map
        - size (uint32): Size of the ADT file
        - flags (uint32): Flags for this map tile
        - asyncID (uint32): Asynchronous loading ID
        """
        entry_size = 16  # Size of SMAreaInfo entry
        entries = []
        
        # Verify data size
        if len(data) != 64 * 64 * entry_size:
            raise ValueError(f"Invalid MAIN chunk size. Expected {64 * 64 * entry_size}, got {len(data)}")
        
        # Parse 64x64 grid of entries
        for y in range(64):
            for x in range(64):
                i = (y * 64 + x)
                entry_data = data[i * entry_size:(i + 1) * entry_size]
                offset, size, flags, async_id = struct.unpack('<4I', entry_data)
                
                flags_decoded = {
                    'has_adt': bool(flags & 0x1),
                    'loaded': bool(flags & 0x2),
                    'loaded_async': bool(flags & 0x4),
                    'has_mccv': bool(flags & 0x8),
                    'has_big_alpha': bool(flags & 0x10),
                    'has_terrain': bool(flags & 0x20),
                    'has_vertex_colors': bool(flags & 0x40)
                }
                
                # Create entry with coordinates and data
                entry = {
                    'offset': offset,
                    'size': size,
                    'flags': flags,
                    'flags_decoded': flags_decoded,
                    'async_id': async_id,
                    'coordinates': {'x': x, 'y': y}
                }
                
                # Consider tile active if it has an offset
                if offset > 0:
                    tile = MapTile(
                        x=x,
                        y=y,
                        offset=offset,
                        size=size,
                        flags=flags,
                        async_id=async_id,
                        has_adt=True
                    )
                    self.tiles[(x, y)] = tile
                    entries.append(entry)
                    
                    # Store in database if available
                    if self.db and self.wdt_id:
                        self.db.insert_map_tile(
                            self.wdt_id,
                            x, y,
                            offset,
                            size,
                            flags,
                            async_id
                        )
                    
                    self.logger.info(f"Found active tile at ({x}, {y}): Offset = {offset}, Size = {size}, Flags = {flags:#x}")
                    for flag_name, flag_value in flags_decoded.items():
                        if flag_value:
                            self.logger.info(f"  {flag_name}: {flag_value}")
        
        return {'entries': entries}
    
    def parse(self) -> Dict[str, Any]:
        """
        Parse Alpha format WDT file
        
        Returns:
            Dictionary containing parsed WDT data
        """
        result = {
            'format': 'alpha',
            'version': None,
            'flags': None,
            'tiles': [],
            'm2_models': [],
            'wmo_models': [],
            'errors': []
        }
        
        try:
            # First pass: Process core chunks
            for header, data in self.iterate_chunks():
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
                    
                    if header.name == 'MVER':
                        result.update(self.parse_chunk(header, data))
                    elif header.name == 'MPHD':
                        flags_data = self.parse_chunk(header, data)
                        result['flags'] = flags_data['flags']
                        result['flags_decoded'] = flags_data['decoded_flags']
                    elif header.name == 'MAIN':
                        main_data = self.parse_chunk(header, data)
                        result['tiles'] = main_data['entries']
                    elif header.name == 'MTEX':
                        mtex_data = self.parse_chunk(header, data)
                        result['textures'] = mtex_data['textures']
                except Exception as e:
                    result['errors'].append(f"Error parsing {header.name} chunk: {e}")
            
            # Second pass: Process model data
            for header, data in self.iterate_chunks():
                try:
                    if header.name == 'MDNM':
                        model_data = self.parse_chunk(header, data)
                        result['m2_models'] = model_data['names']
                    elif header.name == 'MONM':
                        model_data = self.parse_chunk(header, data)
                        result['wmo_models'] = model_data['names']
                except Exception as e:
                    result['errors'].append(f"Error parsing {header.name} chunk: {e}")
            
            # Process any MCNK chunks (Alpha specific)
            mcnk_data = []
            for header, data in self.get_chunks_by_name('MCNK'):
                try:
                    chunk_data = self.parse_chunk(header, data)
                    mcnk_data.append(chunk_data)
                except Exception as e:
                    result['errors'].append(f"Error parsing MCNK chunk: {e}")
            
            if mcnk_data:
                result['mcnk_chunks'] = mcnk_data
            
            # Add chunk order to result
            result['chunk_order'] = ','.join(self.chunk_order)
            
        except Exception as e:
            result['errors'].append(f"Error parsing WDT file: {e}")
        
        return result
    
    def parse_adt(self, tile: MapTile) -> Dict[str, Any]:
        """
        Parse ADT file for a given tile (Alpha format)
        
        Args:
            tile: MapTile object containing tile information
            
        Returns:
            Dictionary containing parsed ADT data
        """
        # For Alpha format, ADT data is embedded in the WDT
        # Get the raw ADT data from the WDT file
        adt_data = self.get_data_at_offset(tile.offset, tile.size)
        
        # Connect database to ADT parser
        if self.db and self.wdt_id:
            self.adt_parser.db = self.db
            self.adt_parser.wdt_id = self.wdt_id
        
        # Parse the embedded ADT data
        return self.adt_parser.parse_embedded_data(adt_data, tile.x, tile.y)