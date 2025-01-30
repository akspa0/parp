"""
Retail format WDT parser implementation.
"""
from typing import Dict, Any, List, Tuple
import struct
import logging
from pathlib import Path

from wdt_adt_parser.base.wdt_parser import WDTParser, MapTile, ModelPlacement

class RetailWDTParser(WDTParser):
    """Parser for Retail format WDT files"""
    
    def _setup_chunk_registry(self) -> None:
        """Register Retail-specific chunk parsers"""
        super()._setup_chunk_registry()
        self.chunk_registry.update({
            'MWMO': self._parse_mwmo,  # WMO model names
            'MWID': self._parse_mwid,  # WMO indices
            'MODF': self._parse_modf,  # WMO placements
            'MMDX': self._parse_mmdx,  # M2 model names
            'MMID': self._parse_mmid,  # M2 indices
            'MDDF': self._parse_mddf,  # M2 placements
            'MHDR': self._parse_mhdr,  # Map header
        })
    
    def _parse_mhdr(self, data: bytes) -> Dict[str, Any]:
        """Parse MHDR (Map Header) chunk"""
        if len(data) < 64:
            raise ValueError(f"Invalid MHDR chunk size: {len(data)}")
        
        offsets = {}
        offset_names = ['mmdx', 'mmid', 'mwmo', 'mwid', 'mddf', 'modf', 'mfbo', 'mh2o']
        
        for i, name in enumerate(offset_names):
            offset = struct.unpack('<I', data[i*4:(i+1)*4])[0]
            if offset > 0:
                offsets[name] = offset
        
        return {'offsets': offsets}
    
    def _parse_mwmo(self, data: bytes) -> Dict[str, Any]:
        """Parse MWMO (WMO Names) chunk"""
        names = data.split(b'\0')
        self.wmo_models = [name.decode('utf-8', 'ignore') for name in names if name]
        return {'names': self.wmo_models}
    
    def _parse_mwid(self, data: bytes) -> Dict[str, Any]:
        """Parse MWID (WMO Indices) chunk"""
        count = len(data) // 4
        indices = struct.unpack(f'<{count}I', data)
        return {'indices': list(indices)}
    
    def _parse_modf(self, data: bytes) -> Dict[str, Any]:
        """Parse MODF (WMO Placements) chunk"""
        entry_size = 64
        if len(data) % entry_size != 0:
            raise ValueError(f"Invalid MODF chunk size: {len(data)}")
        
        entry_count = len(data) // entry_size
        entries = []
        
        for i in range(entry_count):
            entry_data = data[i * entry_size:(i + 1) * entry_size]
            name_id, unique_id = struct.unpack('<II', entry_data[:8])
            position = struct.unpack('<3f', entry_data[8:20])
            rotation = struct.unpack('<3f', entry_data[20:32])
            bounds = struct.unpack('<6f', entry_data[32:56])  # min/max bounds
            flags, doodad_set, name_set, scale = struct.unpack('<HHHH', entry_data[56:64])
            
            placement = ModelPlacement(
                name_id=name_id,
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
        """Parse MMDX (M2 Names) chunk"""
        names = data.split(b'\0')
        self.m2_models = [name.decode('utf-8', 'ignore') for name in names if name]
        return {'names': self.m2_models}
    
    def _parse_mmid(self, data: bytes) -> Dict[str, Any]:
        """Parse MMID (M2 Indices) chunk"""
        count = len(data) // 4
        indices = struct.unpack(f'<{count}I', data)
        return {'indices': list(indices)}
    
    def _parse_mddf(self, data: bytes) -> Dict[str, Any]:
        """Parse MDDF (M2 Placements) chunk"""
        entry_size = 36
        if len(data) % entry_size != 0:
            raise ValueError(f"Invalid MDDF chunk size: {len(data)}")
        
        entry_count = len(data) // entry_size
        entries = []
        
        for i in range(entry_count):
            entry_data = data[i * entry_size:(i + 1) * entry_size]
            name_id, unique_id = struct.unpack('<II', entry_data[:8])
            position = struct.unpack('<3f', entry_data[8:20])
            rotation = struct.unpack('<3f', entry_data[20:32])
            scale, flags = struct.unpack('<HH', entry_data[32:36])
            
            placement = ModelPlacement(
                name_id=name_id,
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
    
    def parse(self) -> Dict[str, Any]:
        """
        Parse Retail format WDT file
        
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
            'm2_placements': [],
            'wmo_placements': [],
            'errors': []
        }
        
        try:
            # First pass: Process core chunks
            for header, data in self.iterate_chunks():
                try:
                    if header.name == 'MVER':
                        result.update(self.parse_chunk(header, data))
                    elif header.name == 'MPHD':
                        flags_data = self.parse_chunk(header, data)
                        result['flags'] = flags_data['flags']
                        result['flags_decoded'] = flags_data['decoded_flags']
                    elif header.name == 'MAIN':
                        main_data = self.parse_chunk(header, data)
                        result['tiles'] = main_data['entries']
                    elif header.name == 'MHDR':
                        result['header'] = self.parse_chunk(header, data)
                except Exception as e:
                    result['errors'].append(f"Error parsing {header.name} chunk: {e}")
            
            # Second pass: Process model data
            for header, data in self.iterate_chunks():
                try:
                    if header.name == 'MMDX':
                        model_data = self.parse_chunk(header, data)
                        result['m2_models'] = model_data['names']
                    elif header.name == 'MWMO':
                        model_data = self.parse_chunk(header, data)
                        result['wmo_models'] = model_data['names']
                    elif header.name == 'MDDF':
                        placement_data = self.parse_chunk(header, data)
                        result['m2_placements'] = placement_data['entries']
                    elif header.name == 'MODF':
                        placement_data = self.parse_chunk(header, data)
                        result['wmo_placements'] = placement_data['entries']
                except Exception as e:
                    result['errors'].append(f"Error parsing {header.name} chunk: {e}")
            
        except Exception as e:
            result['errors'].append(f"Error parsing WDT file: {e}")
        
        return result
    
    def parse_adt(self, tile: MapTile) -> Dict[str, Any]:
        """
        Parse ADT file for a given tile (Retail format)
        
        Args:
            tile: MapTile object containing tile information
            
        Returns:
            Dictionary containing parsed ADT data
        """
        # In Retail format, ADT files are separate
        # This would need to load and parse the corresponding ADT file
        return {
            'format': 'retail',
            'coordinates': {'x': tile.x, 'y': tile.y},
            'error': 'ADT parsing requires loading external ADT file'
        }