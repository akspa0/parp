"""
Alpha format ADT parser implementation
"""

import struct
from typing import Dict, List, Optional, Tuple, Set
from ...base.adt_parser import ADTParserBase, MCNKInfo, TextureInfo, ModelPlacement
from ...base.chunk_parser import ChunkParsingError, ChunkInfo
from ...format_detector import FileFormat

class AlphaADTParser(ADTParserBase):
    """Parser for Alpha format ADT files"""

    # Alpha-specific chunk names
    MDNM_CHUNK = b'MDNM'  # M2 model filenames
    MONM_CHUNK = b'MONM'  # WMO model filenames
    MAOC_CHUNK = b'MAOC'  # Map object coordinates
    MAOF_CHUNK = b'MAOF'  # Map object flags
    MTEX_CHUNK = b'MTEX'  # Texture filenames (simpler format)

    # MCNK subchunk structure is different in Alpha
    ALPHA_MCNK_HEADER_SIZE = 0x80  # 128 bytes
    
    def __init__(self, file_path: str, reversed_chunks: bool = False):
        super().__init__(file_path, FileFormat.ALPHA, reversed_chunks)
        self._model_names: List[str] = []
        self._wmo_names: List[str] = []
        self._model_coords: List[Tuple[float, float, float]] = []
        self._model_flags: List[int] = []

    def _parse_mcnk_header(self, data: bytes) -> Dict[str, any]:
        """Parse Alpha format MCNK header structure"""
        if len(data) < self.ALPHA_MCNK_HEADER_SIZE:
            raise ChunkParsingError("MCNK header too small")
            
        try:
            # Alpha format header structure
            header = {
                'flags': struct.unpack('<I', data[0:4])[0],
                'index_x': struct.unpack('<I', data[4:8])[0],
                'index_y': struct.unpack('<I', data[8:12])[0],
                'layers': struct.unpack('<I', data[12:16])[0],
                'doodad_refs': struct.unpack('<I', data[16:20])[0],
                'position': self.read_vec3d(data, 20),
                'area_id': struct.unpack('<I', data[32:36])[0],
                'liquid_type': struct.unpack('<I', data[36:40])[0],
                'holes': struct.unpack('<I', data[40:44])[0],
                'terrain_type': struct.unpack('<I', data[44:48])[0],
                'predTex': struct.unpack('<I', data[48:52])[0],
                'effect_doodad': struct.unpack('<I', data[52:56])[0],
                'height_offset': struct.unpack('<f', data[56:60])[0]
            }
            
            return header
            
        except Exception as e:
            self.logger.error(f"Error parsing Alpha MCNK header: {e}")
            raise ChunkParsingError("Failed to parse MCNK header") from e

    def _parse_height_map(self, data: bytes) -> List[float]:
        """Parse Alpha format height map (MCVT)"""
        try:
            # Alpha format uses a different height map structure
            heights = []
            pos = 0
            while pos + 4 <= len(data):
                height = struct.unpack('<f', data[pos:pos+4])[0]
                heights.append(height)
                pos += 4
            return heights
        except Exception as e:
            self.logger.error(f"Error parsing height map: {e}")
            raise ChunkParsingError("Failed to parse height map") from e

    def _parse_texture_chunk(self, data: bytes) -> List[TextureInfo]:
        """Parse Alpha format texture information"""
        try:
            textures = []
            pos = 0
            while pos < len(data):
                # Read null-terminated string
                name, next_pos = self.read_padded_string(data, pos)
                if name:
                    textures.append(TextureInfo(
                        filename=name,
                        flags=0,  # Alpha format doesn't have texture flags
                        effect_id=None,
                        is_terrain=True
                    ))
                pos = next_pos
            return textures
        except Exception as e:
            self.logger.error(f"Error parsing texture chunk: {e}")
            raise ChunkParsingError("Failed to parse texture information") from e

    def _parse_liquid_data(self, data: bytes) -> Dict[str, any]:
        """Parse Alpha format liquid data (MCLQ)"""
        try:
            if len(data) < 8:
                return {}
                
            # Alpha format liquid header
            flags = struct.unpack('<I', data[0:4])[0]
            min_height = struct.unpack('<f', data[4:8])[0]
            
            # Parse height data if present
            heights = []
            pos = 8
            while pos + 4 <= len(data):
                height = struct.unpack('<f', data[pos:pos+4])[0]
                heights.append(height)
                pos += 4
                
            return {
                'flags': flags,
                'min_height': min_height,
                'heights': heights
            }
            
        except Exception as e:
            self.logger.error(f"Error parsing liquid data: {e}")
            raise ChunkParsingError("Failed to parse liquid data") from e

    def parse_mcnk(self, chunk: ChunkInfo) -> MCNKInfo:
        """Parse an Alpha format MCNK chunk"""
        data = self.read_chunk(chunk)
        header = self._parse_mcnk_header(data)
        subchunks = self._find_mcnk_subchunks(data)
        
        return MCNKInfo(
            index=header['index_x'] + header['index_y'] * 16,
            x=header['index_x'],
            y=header['index_y'],
            flags=header['flags'],
            area_id=header['area_id'],
            holes=header['holes'],
            subchunks=subchunks,
            liquid_type=header['liquid_type'],
            position=header['position'],
            num_layers=header['layers']
        )

    def parse_textures(self):
        """Parse Alpha format texture information"""
        for chunk in self.find_chunks(self.MTEX_CHUNK):
            textures = self._parse_texture_chunk(self.read_chunk(chunk))
            self._textures.extend(textures)

    def parse_models(self):
        """Parse Alpha format model information"""
        # Parse M2 models
        for chunk in self.find_chunks(self.MDNM_CHUNK):
            data = self.read_chunk(chunk)
            pos = 0
            while pos < len(data):
                name, next_pos = self.read_padded_string(data, pos)
                if name:
                    self._m2_models.append(name)
                pos = next_pos
        
        # Parse WMO models
        for chunk in self.find_chunks(self.MONM_CHUNK):
            data = self.read_chunk(chunk)
            pos = 0
            while pos < len(data):
                name, next_pos = self.read_padded_string(data, pos)
                if name:
                    self._wmo_models.append(name)
                pos = next_pos

    def parse_model_placements(self):
        """Parse Alpha format model placement information"""
        # Parse coordinates
        coords = []
        for chunk in self.find_chunks(self.MAOC_CHUNK):
            data = self.read_chunk(chunk)
            pos = 0
            while pos + 12 <= len(data):
                coords.append(self.read_vec3d(data, pos))
                pos += 12
        
        # Parse flags
        flags = []
        for chunk in self.find_chunks(self.MAOF_CHUNK):
            data = self.read_chunk(chunk)
            count = len(data) // 4
            flags.extend(struct.unpack(f'<{count}I', data))
        
        # Create placements
        for i, (coord, flag) in enumerate(zip(coords, flags)):
            # Determine if this is an M2 or WMO based on flags
            is_m2 = (flag & 0x1) == 0
            
            placement = ModelPlacement(
                name_id=i,
                unique_id=i,  # Alpha format doesn't have unique IDs
                position=coord,
                rotation=(0.0, 0.0, 0.0),  # Alpha format doesn't store rotation
                scale=1.0,  # Alpha format doesn't store scale
                flags=flag
            )
            
            if is_m2:
                self._m2_placements.append(placement)
            else:
                self._wmo_placements.append(placement)

    def validate(self) -> bool:
        """Validate Alpha format specific requirements"""
        if not super().validate():
            return False
            
        # Check for required chunks
        if not self.has_chunk(self.MTEX_CHUNK):
            self.logger.warning("Missing MTEX chunk")
            
        # Validate MCNK structure
        for mcnk in self.iter_mcnks():
            if not mcnk.subchunks:
                self.logger.error(f"MCNK at ({mcnk.x}, {mcnk.y}) has no subchunks")
                return False
                
        return True

    def parse(self) -> Dict[str, any]:
        """Parse Alpha format ADT file"""
        # Parse base data first
        result = super().parse()
        
        # Add Alpha-specific data
        result.update({
            'format': 'ALPHA',
            'terrain_type': next(
                (mcnk.terrain_type for mcnk in self._mcnk_chunks.values() if hasattr(mcnk, 'terrain_type')),
                0
            )
        })
        
        return result