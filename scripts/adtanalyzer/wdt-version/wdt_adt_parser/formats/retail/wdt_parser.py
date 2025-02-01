"""
Retail format WDT parser implementation.
"""
from typing import Dict, Any, List, Tuple, Optional
import struct
import logging
from pathlib import Path

from wdt_adt_parser.base.wdt_parser import WDTParser, MapTile, ModelPlacement
from wdt_adt_parser.database import DatabaseManager
from wdt_adt_parser.formats.retail.adt_parser import RetailADTParser

class RetailWDTParser(WDTParser):
    """Parser for Retail format WDT files"""
    
    def __init__(self):
        """Initialize the Retail WDT parser"""
        super().__init__()
        self.db: Optional[DatabaseManager] = None
        self.wdt_id: Optional[int] = None
        self.chunk_order: List[str] = []
        self.m2_models: List[str] = []
        self.wmo_models: List[str] = []
        self.version: Optional[int] = None
        self.adt_parser = RetailADTParser()
    
    def _setup_chunk_registry(self) -> None:
        """Register Retail-specific chunk parsers"""
        super()._setup_chunk_registry()
        self.chunk_registry.update({
            'MVER': self._parse_mver,  # Version info
            'MPHD': self._parse_mphd,  # Map header
            'MAIN': self._parse_main,  # Map tile table
            'MWMO': self._parse_mwmo,  # WMO filenames
            'MWID': self._parse_mwid,  # WMO indices
            'MODF': self._parse_modf,  # WMO placement
            'MMDX': self._parse_mmdx,  # M2 filenames
            'MMID': self._parse_mmid,  # M2 indices
            'MDDF': self._parse_mddf,  # M2 placement
        })
    
    def _parse_mver(self, data: bytes) -> Dict[str, Any]:
        """Parse MVER (Version) chunk"""
        if len(data) < 4:
            raise ValueError(f"Invalid MVER chunk size: {len(data)}")
        
        version = struct.unpack('<I', data[:4])[0]
        self.version = version
        
        self.logger.info(f"WDT Version: {version}")
        
        return {'version': version}
    
    def _parse_mphd(self, data: bytes) -> Dict[str, Any]:
        """Parse MPHD (Map Header) chunk"""
        if len(data) < 32:  # Retail MPHD size
            raise ValueError(f"Invalid MPHD chunk size: {len(data)}")
        
        flags = struct.unpack('<I', data[:4])[0]
        
        # Decode flags
        flags_decoded = {
            'wdt_has_mwmo': bool(flags & 0x1),
            'use_global_map_obj': bool(flags & 0x2),
            'has_doodad_refs': bool(flags & 0x8),
            'has_terrain': bool(flags & 0x10),
            'has_normal_maps': bool(flags & 0x20),
            'has_vertex_colors': bool(flags & 0x40),
            'has_height_texturing': bool(flags & 0x80),
            'has_water_layers': bool(flags & 0x100)
        }
        
        # Log decoded flags
        self.logger.info(f"Map Header Flags: {flags:#x}")
        for flag_name, flag_value in flags_decoded.items():
            if flag_value:
                self.logger.info(f"  {flag_name}: {flag_value}")
        
        return {
            'flags': flags,
            'decoded_flags': flags_decoded
        }
    
    def _parse_main(self, data: bytes) -> Dict[str, Any]:
        """Parse MAIN (Map Tile Table) chunk"""
        entry_size = 8  # Retail uses 8-byte entries
        entries = []
        
        # Verify data size
        if len(data) != 64 * 64 * entry_size:
            raise ValueError(f"Invalid MAIN chunk size. Expected {64 * 64 * entry_size}, got {len(data)}")
        
        # Parse 64x64 grid of entries
        for y in range(64):
            for x in range(64):
                i = (y * 64 + x)
                entry_data = data[i * entry_size:(i + 1) * entry_size]
                flags, async_id = struct.unpack('<2I', entry_data)
                
                # Decode flags
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
                    'flags': flags,
                    'flags_decoded': flags_decoded,
                    'async_id': async_id,
                    'coordinates': {'x': x, 'y': y}
                }
                
                # Consider tile active if it has ADT flag
                if flags & 0x1:
                    self.active_tiles += 1
                    tile = MapTile(
                        x=x,
                        y=y,
                        offset=0,  # Not used in Retail
                        size=0,    # Not used in Retail
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
                            0,  # offset not used in Retail
                            0,  # size not used in Retail
                            flags,
                            async_id
                        )
                    
                    self.logger.info(f"Found active tile at ({x}, {y}): Flags = {flags:#x}")
                    for flag_name, flag_value in flags_decoded.items():
                        if flag_value:
                            self.logger.info(f"  {flag_name}: {flag_value}")
        
        self.logger.info(f"Found {self.active_tiles} active tiles")
        return {'entries': entries}
    
    def _parse_mwmo(self, data: bytes) -> Dict[str, Any]:
        """Parse MWMO (WMO Filenames) chunk"""
        names = data.split(b'\0')
        models = [name.decode('utf-8', 'ignore') for name in names if name]
        
        # Store for later use
        self.wmo_models = models
        
        # Store in database if available
        if self.db and self.wdt_id:
            for name in models:
                self.db.insert_wmo_model(
                    self.wdt_id,
                    -1, -1,  # Global model list
                    name,
                    'retail'
                )
        
        return {'models': models}
    
    def _parse_mwid(self, data: bytes) -> Dict[str, Any]:
        """Parse MWID (WMO Indices) chunk"""
        count = len(data) // 4
        indices = struct.unpack(f'<{count}I', data)
        return {'indices': list(indices)}
    
    def _parse_modf(self, data: bytes) -> Dict[str, Any]:
        """Parse MODF (WMO Placement) chunk"""
        entry_size = 64
        entries = []
        
        for i in range(0, len(data), entry_size):
            entry_data = data[i:i + entry_size]
            if len(entry_data) < entry_size:
                break
                
            name_id, unique_id = struct.unpack('<2I', entry_data[:8])
            position = struct.unpack('<3f', entry_data[8:20])
            rotation = struct.unpack('<3f', entry_data[20:32])
            bounds = struct.unpack('<6f', entry_data[32:56])
            flags, doodad_set, name_set, scale = struct.unpack('<4H', entry_data[56:64])
            
            placement = ModelPlacement(
                unique_id=unique_id,
                position=position,
                rotation=rotation,
                scale=scale / 1024.0,
                flags=flags
            )
            self.wmo_placements.append(placement)
            
            entries.append({
                'name_id': name_id,
                'unique_id': unique_id,
                'position': {'x': position[0], 'y': position[1], 'z': position[2]},
                'rotation': {'x': rotation[0], 'y': rotation[1], 'z': rotation[2]},
                'bounds': {
                    'min': {'x': bounds[0], 'y': bounds[1], 'z': bounds[2]},
                    'max': {'x': bounds[3], 'y': bounds[4], 'z': bounds[5]}
                },
                'flags': flags,
                'doodad_set': doodad_set,
                'name_set': name_set,
                'scale': scale / 1024.0
            })
        
        return {'entries': entries}
    
    def _parse_mmdx(self, data: bytes) -> Dict[str, Any]:
        """Parse MMDX (M2 Filenames) chunk"""
        names = data.split(b'\0')
        models = [name.decode('utf-8', 'ignore') for name in names if name]
        
        # Store for later use
        self.m2_models = models
        
        # Store in database if available
        if self.db and self.wdt_id:
            for name in models:
                self.db.insert_m2_model(
                    self.wdt_id,
                    -1, -1,  # Global model list
                    name,
                    'retail'
                )
        
        return {'models': models}
    
    def _parse_mmid(self, data: bytes) -> Dict[str, Any]:
        """Parse MMID (M2 Indices) chunk"""
        count = len(data) // 4
        indices = struct.unpack(f'<{count}I', data)
        return {'indices': list(indices)}
    
    def _parse_mddf(self, data: bytes) -> Dict[str, Any]:
        """Parse MDDF (M2 Placement) chunk"""
        entry_size = 36
        entries = []
        
        for i in range(0, len(data), entry_size):
            entry_data = data[i:i + entry_size]
            if len(entry_data) < entry_size:
                break
                
            name_id, unique_id = struct.unpack('<2I', entry_data[:8])
            position = struct.unpack('<3f', entry_data[8:20])
            rotation = struct.unpack('<3f', entry_data[20:32])
            scale, flags = struct.unpack('<2H', entry_data[32:36])
            
            placement = ModelPlacement(
                unique_id=unique_id,
                position=position,
                rotation=rotation,
                scale=scale / 1024.0,
                flags=flags
            )
            self.m2_placements.append(placement)
            
            entries.append({
                'name_id': name_id,
                'unique_id': unique_id,
                'position': {'x': position[0], 'y': position[1], 'z': position[2]},
                'rotation': {'x': rotation[0], 'y': rotation[1], 'z': rotation[2]},
                'scale': scale / 1024.0,
                'flags': flags
            })
        
        return {'entries': entries}
    
    def _process_file_structure(self) -> Dict[str, Any]:
        """Process file structure phase"""
        results = {
            'format': 'retail',
            'version': None,
            'flags': None,
            'errors': []
        }
        
        try:
            for header, data in self.iterate_chunks():
                if header.name == 'MVER':
                    results.update(self.parse_chunk(header, data))
                elif header.name == 'MPHD':
                    flags_data = self.parse_chunk(header, data)
                    results['flags'] = flags_data['flags']
                    results['flags_decoded'] = flags_data['decoded_flags']
                
                # Track chunk order
                self.chunk_order.append(header.name)
                
                # Store chunk offset
                self.store_chunk_offset(header)
                
        except Exception as e:
            results['errors'].append(f"Error in file structure phase: {e}")
            
        return results
    
    def _process_chunks(self) -> Dict[str, Any]:
        """Process chunks phase"""
        results = {
            'tiles': [],
            'errors': []
        }
        
        try:
            for header, data in self.iterate_chunks():
                if header.name == 'MAIN':
                    main_data = self.parse_chunk(header, data)
                    results['tiles'] = main_data['entries']
                    break  # MAIN chunk processed
                    
        except Exception as e:
            results['errors'].append(f"Error in chunk processing phase: {e}")
            
        return results
    
    def _process_map_structure(self) -> Dict[str, Any]:
        """Process map structure phase"""
        results = {
            'active_tiles': self.active_tiles,
            'grid': self.grid,
            'errors': []
        }
        
        try:
            # Generate visualizations
            vis_files = self.generate_visualizations()
            results['visualizations'] = vis_files
            
        except Exception as e:
            results['errors'].append(f"Error in map structure phase: {e}")
            
        return results
    
    def _process_assets(self) -> Dict[str, Any]:
        """Process assets phase"""
        results = {
            'm2_models': [],
            'wmo_models': [],
            'm2_placements': [],
            'wmo_placements': [],
            'errors': []
        }
        
        try:
            # Process model data
            for header, data in self.iterate_chunks():
                if header.name == 'MMDX':
                    model_data = self.parse_chunk(header, data)
                    results['m2_models'] = model_data['models']
                elif header.name == 'MWMO':
                    model_data = self.parse_chunk(header, data)
                    results['wmo_models'] = model_data['models']
                elif header.name == 'MDDF':
                    placement_data = self.parse_chunk(header, data)
                    results['m2_placements'] = placement_data['entries']
                elif header.name == 'MODF':
                    placement_data = self.parse_chunk(header, data)
                    results['wmo_placements'] = placement_data['entries']
                    
        except Exception as e:
            results['errors'].append(f"Error in asset processing phase: {e}")
            
        return results
    
    def parse(self) -> Dict[str, Any]:
        """
        Parse Retail format WDT file using multi-phase approach
        
        Returns:
            Dictionary containing parsed WDT data
        """
        result = {
            'format': 'retail',
            'version': None,
            'flags': None,
            'tiles': [],
            'm2_models': [],
            'wmo_models': [],
            'errors': [],
            'phase_results': {}
        }
        
        try:
            # Process each phase
            for phase in ParsingPhase:
                phase_result = self.process_phase(phase)
                result['phase_results'][phase.name] = phase_result
                
                # Update main result with phase data
                if phase == ParsingPhase.FILE_STRUCTURE:
                    result.update({
                        'version': phase_result.get('version'),
                        'flags': phase_result.get('flags'),
                        'flags_decoded': phase_result.get('flags_decoded')
                    })
                elif phase == ParsingPhase.CHUNK_PROCESSING:
                    result['tiles'] = phase_result.get('tiles', [])
                elif phase == ParsingPhase.MAP_STRUCTURE:
                    result['visualizations'] = phase_result.get('visualizations', {})
                elif phase == ParsingPhase.ASSET_PROCESSING:
                    result['m2_models'] = phase_result.get('m2_models', [])
                    result['wmo_models'] = phase_result.get('wmo_models', [])
                    result['m2_placements'] = phase_result.get('m2_placements', [])
                    result['wmo_placements'] = phase_result.get('wmo_placements', [])
                
                # Collect any errors
                if 'errors' in phase_result and phase_result['errors']:
                    result['errors'].extend(phase_result['errors'])
            
            # Add chunk order to result
            result['chunk_order'] = ','.join(self.chunk_order)
            
        except Exception as e:
            result['errors'].append(f"Error parsing WDT file: {e}")
        
        return result