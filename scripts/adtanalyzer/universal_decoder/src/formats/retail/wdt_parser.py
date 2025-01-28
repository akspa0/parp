"""
Retail format WDT parser implementation
"""

import struct
from typing import Dict, List, Optional, Tuple
from ...base.wdt_parser import WDTParserBase, MapTile, ModelReference
from ...base.chunk_parser import ChunkParsingError
from ...format_detector import FileFormat

class RetailWDTParser(WDTParserBase):
    """Parser for Retail format WDT files"""

    # Retail-specific chunk names
    MMDX_CHUNK = b'MMDX'  # M2 model filenames
    MMID_CHUNK = b'MMID'  # M2 model indices
    MWMO_CHUNK = b'MWMO'  # WMO model filenames
    MWID_CHUNK = b'MWID'  # WMO model indices
    MDDF_CHUNK = b'MDDF'  # M2 model placements
    MODF_CHUNK = b'MODF'  # WMO model placements
    MPHD_CHUNK = b'MPHD'  # Map header (extended)
    
    def __init__(self, file_path: str, reversed_chunks: bool = False):
        super().__init__(file_path, FileFormat.RETAIL, reversed_chunks)
        self._m2_names: List[str] = []
        self._m2_indices: List[int] = []
        self._wmo_names: List[str] = []
        self._wmo_indices: List[int] = []
        self._m2_placements: List[ModelReference] = []
        self._wmo_placements: List[ModelReference] = []

    def _parse_mphd_chunk(self, chunk_data: bytes) -> Dict[str, any]:
        """Parse MPHD chunk containing extended map header"""
        try:
            if len(chunk_data) < 32:  # Minimum size for retail MPHD
                raise ChunkParsingError("MPHD chunk too small")
                
            return {
                'flags': struct.unpack('<I', chunk_data[0:4])[0],
                'something': struct.unpack('<I', chunk_data[4:8])[0],
                'unused': list(struct.unpack('<5I', chunk_data[8:28])),
                'map_id': struct.unpack('<I', chunk_data[28:32])[0]
            }
        except Exception as e:
            self.logger.error(f"Error parsing MPHD chunk: {e}")
            raise ChunkParsingError("Failed to parse map header") from e

    def _parse_mmdx_chunk(self, chunk_data: bytes) -> List[str]:
        """Parse MMDX chunk containing M2 model filenames"""
        try:
            names = []
            pos = 0
            while pos < len(chunk_data):
                name, next_pos = self.read_padded_string(chunk_data, pos)
                if name:
                    names.append(name)
                pos = next_pos
            return names
        except Exception as e:
            self.logger.error(f"Error parsing MMDX chunk: {e}")
            raise ChunkParsingError("Failed to parse M2 model names") from e

    def _parse_mmid_chunk(self, chunk_data: bytes) -> List[int]:
        """Parse MMID chunk containing M2 model indices"""
        try:
            count = len(chunk_data) // 4
            return list(struct.unpack(f'<{count}I', chunk_data))
        except Exception as e:
            self.logger.error(f"Error parsing MMID chunk: {e}")
            raise ChunkParsingError("Failed to parse M2 model indices") from e

    def _parse_mwmo_chunk(self, chunk_data: bytes) -> List[str]:
        """Parse MWMO chunk containing WMO model filenames"""
        try:
            names = []
            pos = 0
            while pos < len(chunk_data):
                name, next_pos = self.read_padded_string(chunk_data, pos)
                if name:
                    names.append(name)
                pos = next_pos
            return names
        except Exception as e:
            self.logger.error(f"Error parsing MWMO chunk: {e}")
            raise ChunkParsingError("Failed to parse WMO model names") from e

    def _parse_mwid_chunk(self, chunk_data: bytes) -> List[int]:
        """Parse MWID chunk containing WMO model indices"""
        try:
            count = len(chunk_data) // 4
            return list(struct.unpack(f'<{count}I', chunk_data))
        except Exception as e:
            self.logger.error(f"Error parsing MWID chunk: {e}")
            raise ChunkParsingError("Failed to parse WMO model indices") from e

    def _parse_mddf_chunk(self, chunk_data: bytes) -> List[ModelReference]:
        """Parse MDDF chunk containing M2 model placements"""
        try:
            placements = []
            pos = 0
            while pos + 36 <= len(chunk_data):
                name_id = struct.unpack('<I', chunk_data[pos:pos+4])[0]
                unique_id = struct.unpack('<I', chunk_data[pos+4:pos+8])[0]
                position = self.read_vec3d(chunk_data, pos+8)
                rotation = self.read_vec3d(chunk_data, pos+20)
                scale = struct.unpack('<H', chunk_data[pos+32:pos+34])[0] / 1024.0
                flags = struct.unpack('<H', chunk_data[pos+34:pos+36])[0]
                
                placements.append(ModelReference(
                    name=self._m2_names[name_id] if name_id < len(self._m2_names) else "",
                    flags=flags,
                    unique_id=unique_id,
                    position=position,
                    rotation=rotation,
                    scale=scale
                ))
                
                pos += 36
                
            return placements
        except Exception as e:
            self.logger.error(f"Error parsing MDDF chunk: {e}")
            raise ChunkParsingError("Failed to parse M2 placements") from e

    def _parse_modf_chunk(self, chunk_data: bytes) -> List[ModelReference]:
        """Parse MODF chunk containing WMO model placements"""
        try:
            placements = []
            pos = 0
            while pos + 64 <= len(chunk_data):
                name_id = struct.unpack('<I', chunk_data[pos:pos+4])[0]
                unique_id = struct.unpack('<I', chunk_data[pos+4:pos+8])[0]
                position = self.read_vec3d(chunk_data, pos+8)
                rotation = self.read_vec3d(chunk_data, pos+20)
                bounds_min = self.read_vec3d(chunk_data, pos+32)
                bounds_max = self.read_vec3d(chunk_data, pos+44)
                flags = struct.unpack('<H', chunk_data[pos+56:pos+58])[0]
                doodad_set = struct.unpack('<H', chunk_data[pos+58:pos+60])[0]
                name_set = struct.unpack('<H', chunk_data[pos+60:pos+62])[0]
                scale = struct.unpack('<H', chunk_data[pos+62:pos+64])[0] / 1024.0
                
                placements.append(ModelReference(
                    name=self._wmo_names[name_id] if name_id < len(self._wmo_names) else "",
                    flags=flags,
                    unique_id=unique_id,
                    position=position,
                    rotation=rotation,
                    scale=scale,
                    doodad_set=doodad_set,
                    name_set=name_set,
                    bounds_min=bounds_min,
                    bounds_max=bounds_max
                ))
                
                pos += 64
                
            return placements
        except Exception as e:
            self.logger.error(f"Error parsing MODF chunk: {e}")
            raise ChunkParsingError("Failed to parse WMO placements") from e

    def _parse_main_array(self):
        """Parse main array of map tiles (Retail format)"""
        try:
            chunk = next(self.find_chunks(self.MAIN_CHUNK))
            data = self.read_chunk(chunk)
            
            # Retail format uses flags and async_id
            for y in range(64):
                for x in range(64):
                    offset = (y * 64 + x) * 8
                    if offset + 8 > len(data):
                        break
                        
                    flags, async_id = struct.unpack('<II', data[offset:offset+8])
                    has_data = (flags & 0x1) != 0
                    
                    if has_data:
                        self._tiles[(x, y)] = MapTile(
                            x=x,
                            y=y,
                            flags=flags,
                            async_id=async_id,
                            has_data=True,
                            data_offset=0,  # Set later if needed
                            data_size=0     # Set later if needed
                        )
                        
        except StopIteration:
            self.logger.error("No MAIN chunk found")
            raise ChunkParsingError("Failed to parse map tiles: MAIN chunk missing")
        except Exception as e:
            self.logger.error(f"Error parsing MAIN chunk: {e}")
            raise ChunkParsingError("Failed to parse map tiles") from e

    def validate(self) -> bool:
        """Validate Retail format specific requirements"""
        if not super().validate():
            return False
            
        # Check for required Retail chunks
        if not self.has_chunk(self.MPHD_CHUNK):
            self.logger.error("Missing MPHD chunk")
            return False
            
        # Validate model references
        if self._m2_placements and not self._m2_names:
            self.logger.error("M2 placements found but no model names")
            return False
            
        if self._wmo_placements and not self._wmo_names:
            self.logger.error("WMO placements found but no model names")
            return False
            
        return True

    def parse(self) -> Dict[str, any]:
        """Parse Retail format WDT file"""
        # Parse base data first
        result = super().parse()
        
        # Parse Retail-specific chunks
        try:
            # Parse model names and indices
            for chunk in self.find_chunks(self.MMDX_CHUNK):
                self._m2_names.extend(self._parse_mmdx_chunk(self.read_chunk(chunk)))
                
            for chunk in self.find_chunks(self.MMID_CHUNK):
                self._m2_indices.extend(self._parse_mmid_chunk(self.read_chunk(chunk)))
                
            for chunk in self.find_chunks(self.MWMO_CHUNK):
                self._wmo_names.extend(self._parse_mwmo_chunk(self.read_chunk(chunk)))
                
            for chunk in self.find_chunks(self.MWID_CHUNK):
                self._wmo_indices.extend(self._parse_mwid_chunk(self.read_chunk(chunk)))
                
            # Parse model placements
            for chunk in self.find_chunks(self.MDDF_CHUNK):
                self._m2_placements.extend(self._parse_mddf_chunk(self.read_chunk(chunk)))
                
            for chunk in self.find_chunks(self.MODF_CHUNK):
                self._wmo_placements.extend(self._parse_modf_chunk(self.read_chunk(chunk)))
                
            # Parse extended header if present
            mphd_data = {}
            for chunk in self.find_chunks(self.MPHD_CHUNK):
                mphd_data = self._parse_mphd_chunk(self.read_chunk(chunk))
                break
                
            # Add Retail-specific data to result
            result.update({
                'format': 'RETAIL',
                'map_id': mphd_data.get('map_id', 0),
                'm2_models': self._m2_names,
                'wmo_models': self._wmo_names,
                'm2_placements': [
                    {
                        'name': p.name,
                        'unique_id': p.unique_id,
                        'position': p.position,
                        'rotation': p.rotation,
                        'scale': p.scale,
                        'flags': p.flags
                    }
                    for p in self._m2_placements
                ],
                'wmo_placements': [
                    {
                        'name': p.name,
                        'unique_id': p.unique_id,
                        'position': p.position,
                        'rotation': p.rotation,
                        'scale': p.scale,
                        'flags': p.flags,
                        'doodad_set': getattr(p, 'doodad_set', 0),
                        'name_set': getattr(p, 'name_set', 0),
                        'bounds_min': getattr(p, 'bounds_min', (0, 0, 0)),
                        'bounds_max': getattr(p, 'bounds_max', (0, 0, 0))
                    }
                    for p in self._wmo_placements
                ]
            })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing Retail format data: {e}")
            raise ChunkParsingError("Failed to parse Retail format WDT") from e