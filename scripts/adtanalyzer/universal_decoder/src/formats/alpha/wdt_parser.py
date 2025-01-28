"""
Alpha format WDT parser implementation
"""

import struct
from typing import Dict, List, Optional, Tuple
from ...base.wdt_parser import WDTParserBase, MapTile, ModelReference
from ...base.chunk_parser import ChunkParsingError
from ...format_detector import FileFormat

class AlphaWDTParser(WDTParserBase):
    """Parser for Alpha format WDT files"""

    # Alpha-specific chunk names
    MDNM_CHUNK = b'MDNM'  # M2 model filenames
    MONM_CHUNK = b'MONM'  # WMO model filenames
    MAOC_CHUNK = b'MAOC'  # Map object coordinates
    MAOF_CHUNK = b'MAOF'  # Map object flags
    
    def __init__(self, file_path: str, reversed_chunks: bool = False):
        super().__init__(file_path, FileFormat.ALPHA, reversed_chunks)
        self._model_names: List[str] = []
        self._wmo_names: List[str] = []
        self._model_coords: List[Tuple[float, float, float]] = []
        self._model_flags: List[int] = []

    def _parse_mdnm_chunk(self, chunk_data: bytes) -> List[str]:
        """Parse MDNM chunk containing M2 model filenames"""
        try:
            # Alpha format uses null-terminated strings
            names = []
            pos = 0
            while pos < len(chunk_data):
                name, next_pos = self.read_padded_string(chunk_data, pos)
                if name:
                    names.append(name)
                pos = next_pos
                if pos >= len(chunk_data):
                    break
            return names
        except Exception as e:
            self.logger.error(f"Error parsing MDNM chunk: {e}")
            raise ChunkParsingError("Failed to parse M2 model names") from e

    def _parse_monm_chunk(self, chunk_data: bytes) -> List[str]:
        """Parse MONM chunk containing WMO model filenames"""
        try:
            # Similar to MDNM parsing
            names = []
            pos = 0
            while pos < len(chunk_data):
                name, next_pos = self.read_padded_string(chunk_data, pos)
                if name:
                    names.append(name)
                pos = next_pos
                if pos >= len(chunk_data):
                    break
            return names
        except Exception as e:
            self.logger.error(f"Error parsing MONM chunk: {e}")
            raise ChunkParsingError("Failed to parse WMO model names") from e

    def _parse_maoc_chunk(self, chunk_data: bytes) -> List[Tuple[float, float, float]]:
        """Parse MAOC chunk containing model coordinates"""
        try:
            coords = []
            pos = 0
            while pos + 12 <= len(chunk_data):
                coords.append(self.read_vec3d(chunk_data, pos))
                pos += 12
            return coords
        except Exception as e:
            self.logger.error(f"Error parsing MAOC chunk: {e}")
            raise ChunkParsingError("Failed to parse model coordinates") from e

    def _parse_maof_chunk(self, chunk_data: bytes) -> List[int]:
        """Parse MAOF chunk containing model flags"""
        try:
            count = len(chunk_data) // 4
            return list(struct.unpack(f'<{count}I', chunk_data))
        except Exception as e:
            self.logger.error(f"Error parsing MAOF chunk: {e}")
            raise ChunkParsingError("Failed to parse model flags") from e

    def _parse_main_array(self):
        """Parse main array of map tiles (Alpha format)"""
        try:
            chunk = next(self.find_chunks(self.MAIN_CHUNK))
            data = self.read_chunk(chunk)
            
            # Alpha format uses a different tile structure
            for y in range(64):
                for x in range(64):
                    offset = (y * 64 + x) * 4
                    if offset + 4 > len(data):
                        break
                        
                    flags = struct.unpack('<I', data[offset:offset+4])[0]
                    has_data = (flags & 0x1) != 0
                    
                    if has_data:
                        self._tiles[(x, y)] = MapTile(
                            x=x,
                            y=y,
                            flags=flags,
                            async_id=0,  # Not used in Alpha
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
        """Validate Alpha format specific requirements"""
        if not super().validate():
            return False
            
        # Check for required Alpha chunks
        if not self.has_chunk(self.MDNM_CHUNK) and not self.has_chunk(self.MONM_CHUNK):
            self.logger.error("Missing both MDNM and MONM chunks")
            return False
            
        # Validate coordinate data if models exist
        if self._model_names and not self._model_coords:
            self.logger.error("Models defined but no coordinate data found")
            return False
            
        return True

    def parse(self) -> Dict[str, any]:
        """Parse Alpha format WDT file"""
        # Parse base data first
        result = super().parse()
        
        # Parse Alpha-specific chunks
        try:
            # Parse model names
            for chunk in self.find_chunks(self.MDNM_CHUNK):
                self._model_names.extend(self._parse_mdnm_chunk(self.read_chunk(chunk)))
                
            for chunk in self.find_chunks(self.MONM_CHUNK):
                self._wmo_names.extend(self._parse_monm_chunk(self.read_chunk(chunk)))
                
            # Parse model data
            for chunk in self.find_chunks(self.MAOC_CHUNK):
                self._model_coords.extend(self._parse_maoc_chunk(self.read_chunk(chunk)))
                
            for chunk in self.find_chunks(self.MAOF_CHUNK):
                self._model_flags.extend(self._parse_maof_chunk(self.read_chunk(chunk)))
                
            # Add Alpha-specific data to result
            result.update({
                'format': 'ALPHA',
                'm2_models': self._model_names,
                'wmo_models': self._wmo_names,
                'model_placements': [
                    {
                        'index': i,
                        'coordinates': coords,
                        'flags': flags
                    }
                    for i, (coords, flags) in enumerate(
                        zip(self._model_coords, self._model_flags)
                    )
                ]
            })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing Alpha format data: {e}")
            raise ChunkParsingError("Failed to parse Alpha format WDT") from e