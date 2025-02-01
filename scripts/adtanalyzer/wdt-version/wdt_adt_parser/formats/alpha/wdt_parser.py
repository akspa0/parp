"""
Alpha format WDT parser implementation.
"""
from typing import Dict, Any, List, Tuple, Optional
import struct
import logging
from pathlib import Path

from wdt_adt_parser.base.wdt_parser import WDTParser, MapTile
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
        self.m2_models: List[str] = []
        self.wmo_models: List[str] = []
        self.version: Optional[int] = None
        self.adt_parser = AlphaADTParser()
        self.active_tiles = 0
    
    def _setup_chunk_registry(self) -> None:
        """Register Alpha-specific chunk parsers"""
        super()._setup_chunk_registry()
        self.chunk_registry.update({
            'MVER': self._parse_mver,  # Version info
            'MPHD': self._parse_mphd,  # Map header
            'MAIN': self._parse_main,  # Map tile table
            'MDNM': self._parse_mdnm,  # M2 model names
            'MONM': self._parse_monm,  # WMO model names
        })

    def _parse_mver(self, data: bytes) -> Dict[str, Any]:
        """
        Parse MVER (Map Version) chunk
        Contains a single uint32 version number
        """
        if len(data) < 4:
            raise ValueError(f"Invalid MVER chunk size: {len(data)}")
        
        version = struct.unpack('<I', data[:4])[0]
        self.version = version
        
        self.logger.info(f"WDT Version: {version}")
        
        return {'version': version}

    def _parse_mphd(self, data: bytes) -> Dict[str, Any]:
        """
        Parse MPHD (Map Header) chunk
        
        The MPHD chunk contains:
        - flags (uint32): Map flags
        - skip (uint32): Unknown/padding
        - layerCount (uint32): Number of doodad layers
        - skip2 (uint32): Unknown/padding
        """
        if len(data) < 16:  # Minimum size for header
            raise ValueError(f"Invalid MPHD chunk size: {len(data)}")
        
        flags, _, layer_count, _ = struct.unpack('<4I', data[:16])
        
        # Decode flags exactly as in original code
        flags_decoded = {
            'wmo_only': bool(flags & 0x1),
            'no_terrain': bool(flags & 0x2),
            'unk1': bool(flags & 0x4),
            'unk2': bool(flags & 0x8),
            'unk3': bool(flags & 0x10),
            'unk4': bool(flags & 0x20),
            'unk5': bool(flags & 0x40),
            'has_mccv': bool(flags & 0x80)  # Vertex colors
        }
        
        # Log decoded flags
        self.logger.info(f"Map Header Flags: {flags:#x}")
        for flag_name, flag_value in flags_decoded.items():
            if flag_value:
                self.logger.info(f"  {flag_name}: {flag_value}")
        
        return {
            'flags': flags,
            'decoded_flags': flags_decoded,
            'layer_count': layer_count
        }
    
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
                
                # In Alpha format, a tile has an ADT if it has a non-zero offset
                has_adt = offset > 0
                
                # Decode flags
                flags_decoded = {
                    'has_adt': has_adt,
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
                
                # Consider tile active if it has a non-zero offset
                if offset > 0:
                    self.active_tiles += 1
                    tile = MapTile(
                        x=x,
                        y=y,
                        offset=offset,
                        size=size,
                        flags=flags,
                        async_id=async_id,
                        has_adt=True  # If offset > 0, it has ADT data
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
                        
                        # Parse embedded ADT data
                        if size > 0:
                            try:
                                adt_data = self.get_data_at_offset(offset, size)
                                
                                # Connect database to ADT parser
                                self.adt_parser.db = self.db
                                self.adt_parser.wdt_id = self.wdt_id
                                
                                # Parse the embedded ADT data
                                adt_result = self.adt_parser.parse_embedded_data(adt_data, x, y)
                                
                                # Add ADT data to entry for completeness
                                entry['adt_data'] = adt_result
                                
                            except Exception as e:
                                self.logger.error(f"Failed to parse ADT data at ({x}, {y}): {e}")
                    
                    self.logger.info(f"Found active tile at ({x}, {y}): Offset = {offset}, Size = {size}, Flags = {flags:#x}")
                    for flag_name, flag_value in flags_decoded.items():
                        if flag_value:
                            self.logger.info(f"  {flag_name}: {flag_value}")
        
        self.logger.info(f"Found {self.active_tiles} active tiles")
        return {'entries': entries}

    def _parse_mdnm(self, data: bytes) -> Dict[str, Any]:
        """
        Parse MDNM (Map Doodad Names) chunk
        Contains null-terminated strings of M2 model filenames
        """
        names = data.split(b'\0')
        doodad_names = [name.decode('utf-8', 'replace') for name in names if name]
        
        self.logger.info(f"MDNM Chunk: {len(doodad_names)} doodad names")
        for name in doodad_names:
            self.logger.info(f"  Doodad: {name}")
        
        # Store for later use
        self.m2_models = doodad_names
        
        # Store in database if available
        if self.db and self.wdt_id:
            for name in doodad_names:
                self.db.insert_m2_model(
                    self.wdt_id,
                    -1, -1,  # Global model list
                    name,
                    'alpha'
                )
        
        return {'names': doodad_names}

    def _parse_monm(self, data: bytes) -> Dict[str, Any]:
        """
        Parse MONM (Map Object Names) chunk
        Contains null-terminated strings of WMO model filenames
        """
        names = data.split(b'\0')
        object_names = [name.decode('utf-8', 'replace') for name in names if name]
        
        self.logger.info(f"MONM Chunk: {len(object_names)} object names")
        for name in object_names:
            self.logger.info(f"  Object: {name}")
        
        # Store for later use
        self.wmo_models = object_names
        
        # Store in database if available
        if self.db and self.wdt_id:
            for name in object_names:
                self.db.insert_wmo_model(
                    self.wdt_id,
                    -1, -1,  # Global model list
                    name,
                    'alpha'
                )
        
        return {'names': object_names}
    
    def _process_file_structure(self) -> Dict[str, Any]:
        """Process file structure phase"""
        results = {
            'format': 'alpha',
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
            'errors': []
        }
        
        try:
            for header, data in self.iterate_chunks():
                if header.name == 'MDNM':
                    model_data = self.parse_chunk(header, data)
                    results['m2_models'] = model_data['names']
                elif header.name == 'MONM':
                    model_data = self.parse_chunk(header, data)
                    results['wmo_models'] = model_data['names']
                    
        except Exception as e:
            results['errors'].append(f"Error in asset processing phase: {e}")
            
        return results
    
    def parse(self) -> Dict[str, Any]:
        """
        Parse Alpha format WDT file using multi-phase approach
        
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
                
                # Collect any errors
                if 'errors' in phase_result and phase_result['errors']:
                    result['errors'].extend(phase_result['errors'])
            
            # Add chunk order to result
            result['chunk_order'] = ','.join(self.chunk_order)
            
        except Exception as e:
            result['errors'].append(f"Error parsing WDT file: {e}")
        
        return result