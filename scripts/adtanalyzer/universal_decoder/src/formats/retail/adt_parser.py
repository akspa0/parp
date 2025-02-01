"""
Retail format ADT parser implementation
"""

import struct
from typing import Dict, List, Optional, Tuple, Set
from ...base.adt_parser import ADTParserBase, MCNKInfo, TextureInfo, ModelPlacement
from ...base.chunk_parser import ChunkParsingError, ChunkInfo
from ...format_detector import FileFormat

class RetailADTParser(ADTParserBase):
    """Parser for Retail format ADT files"""

    # Retail-specific chunk names
    MMDX_CHUNK = b'MMDX'  # M2 model filenames
    MMID_CHUNK = b'MMID'  # M2 model indices
    MWMO_CHUNK = b'MWMO'  # WMO model filenames
    MWID_CHUNK = b'MWID'  # WMO model indices
    MDDF_CHUNK = b'MDDF'  # M2 model placements
    MODF_CHUNK = b'MODF'  # WMO model placements
    MCNK_CHUNK = b'MCNK'  # Map chunk
    MCVT_CHUNK = b'MCVT'  # Height map
    MCLV_CHUNK = b'MCLV'  # Vertex lighting
    MCCV_CHUNK = b'MCCV'  # Vertex colors
    
    # MCNK subchunk structure for Retail
    RETAIL_MCNK_HEADER_SIZE = 128
    
    def __init__(self, file_path: str, reversed_chunks: bool = False):
        super().__init__(file_path, FileFormat.RETAIL, reversed_chunks)
        self._m2_indices: List[int] = []
        self._wmo_indices: List[int] = []

    def _parse_mcnk_header(self, data: bytes) -> Dict[str, any]:
        """Parse Retail format MCNK header structure"""
        if len(data) < self.RETAIL_MCNK_HEADER_SIZE:
            raise ChunkParsingError("MCNK header too small")
            
        try:
            header = {
                'flags': struct.unpack('<I', data[0:4])[0],
                'index_x': struct.unpack('<I', data[4:8])[0],
                'index_y': struct.unpack('<I', data[8:12])[0],
                'layers': struct.unpack('<I', data[12:16])[0],
                'doodad_refs': struct.unpack('<I', data[16:20])[0],
                'position': self.read_vec3d(data, 20),
                'mcvt_offset': struct.unpack('<I', data[32:36])[0],
                'mcnr_offset': struct.unpack('<I', data[36:40])[0],
                'mcly_offset': struct.unpack('<I', data[40:44])[0],
                'mcrf_offset': struct.unpack('<I', data[44:48])[0],
                'mcal_offset': struct.unpack('<I', data[48:52])[0],
                'mcsh_offset': struct.unpack('<I', data[52:56])[0],
                'size_alpha': struct.unpack('<I', data[56:60])[0],
                'holes': struct.unpack('<I', data[60:64])[0],
                'layer_texture_id': struct.unpack('<I', data[64:68])[0],
                'sound_emitters': struct.unpack('<I', data[68:72])[0],
                'liquid_type': struct.unpack('<I', data[72:76])[0],
                'predTex': struct.unpack('<I', data[76:80])[0],
                'effect_doodad': struct.unpack('<I', data[80:84])[0],
                'mcse_offset': struct.unpack('<I', data[84:88])[0],
                'mclq_offset': struct.unpack('<I', data[88:92])[0]
            }
            
            return header
            
        except Exception as e:
            self.logger.error(f"Error parsing Retail MCNK header: {e}")
            raise ChunkParsingError("Failed to parse MCNK header") from e

    def _parse_texture_layer(self, data: bytes) -> Dict[str, any]:
        """Parse Retail format texture layer (MCLY)"""
        try:
            if len(data) < 16:
                raise ChunkParsingError("Texture layer data too small")
                
            return {
                'texture_id': struct.unpack('<I', data[0:4])[0],
                'flags': struct.unpack('<I', data[4:8])[0],
                'offset_in_mcal': struct.unpack('<I', data[8:12])[0],
                'effect_id': struct.unpack('<I', data[12:16])[0]
            }
        except Exception as e:
            self.logger.error(f"Error parsing texture layer: {e}")
            raise ChunkParsingError("Failed to parse texture layer") from e

    def _parse_model_placement(self, data: bytes, is_m2: bool = True) -> ModelPlacement:
        """Parse Retail format model placement (MDDF/MODF)"""
        try:
            if is_m2:
                # M2 placement (36 bytes)
                if len(data) < 36:
                    raise ChunkParsingError("M2 placement data too small")
                    
                name_id = struct.unpack('<I', data[0:4])[0]
                unique_id = struct.unpack('<I', data[4:8])[0]
                position = self.read_vec3d(data, 8)
                rotation = self.read_vec3d(data, 20)
                scale = struct.unpack('<H', data[32:34])[0] / 1024.0
                flags = struct.unpack('<H', data[34:36])[0]
                
                return ModelPlacement(
                    name_id=name_id,
                    unique_id=unique_id,
                    position=position,
                    rotation=rotation,
                    scale=scale,
                    flags=flags
                )
            else:
                # WMO placement (64 bytes)
                if len(data) < 64:
                    raise ChunkParsingError("WMO placement data too small")
                    
                name_id = struct.unpack('<I', data[0:4])[0]
                unique_id = struct.unpack('<I', data[4:8])[0]
                position = self.read_vec3d(data, 8)
                rotation = self.read_vec3d(data, 20)
                bounds_min = self.read_vec3d(data, 32)
                bounds_max = self.read_vec3d(data, 44)
                flags = struct.unpack('<H', data[56:58])[0]
                doodad_set = struct.unpack('<H', data[58:60])[0]
                name_set = struct.unpack('<H', data[60:62])[0]
                scale = struct.unpack('<H', data[62:64])[0] / 1024.0
                
                return ModelPlacement(
                    name_id=name_id,
                    unique_id=unique_id,
                    position=position,
                    rotation=rotation,
                    scale=scale,
                    flags=flags,
                    doodad_set=doodad_set,
                    name_set=name_set,
                    bounds_min=bounds_min,
                    bounds_max=bounds_max
                )
                
        except Exception as e:
            model_type = "M2" if is_m2 else "WMO"
            self.logger.error(f"Error parsing {model_type} placement: {e}")
            raise ChunkParsingError(f"Failed to parse {model_type} placement") from e

    def parse_mcnk(self, chunk: ChunkInfo) -> MCNKInfo:
        """Parse a Retail format MCNK chunk"""
        data = self.read_chunk(chunk)
        self.logger.debug(f"Parsing MCNK chunk at offset {chunk.offset}, size {chunk.size}")
        
        header = self._parse_mcnk_header(data)
        self.logger.debug(f"MCNK header parsed: flags={header['flags']}, area_id={header.get('layer_texture_id', 0)}")
        
        subchunks = self._find_mcnk_subchunks(data)
        self.logger.debug(f"Found subchunks: {[name.decode('ascii') for name in subchunks.keys()]}")
        
        # Process subchunks
        processed_subchunks = {}
        for name, subchunk in subchunks.items():
            if name == self.MCVT_CHUNK:
                # Height map
                heights = []
                chunk_data = data[subchunk.data_offset:subchunk.data_offset + subchunk.size]
                pos = 0
                while pos + 4 <= len(chunk_data):
                    height = struct.unpack('<f', chunk_data[pos:pos+4])[0]
                    heights.append(height)
                    pos += 4
                processed_subchunks['heights'] = heights
                
            elif name == self.MCLY_CHUNK:
                # Texture layers
                layers = []
                chunk_data = data[subchunk.data_offset:subchunk.data_offset + subchunk.size]
                pos = 0
                while pos + 16 <= len(chunk_data):
                    layer = self._parse_texture_layer(chunk_data[pos:pos+16])
                    layers.append(layer)
                    pos += 16
                processed_subchunks['layers'] = layers
        
        # Create MCNK data structure
        mcnk_data = {
            'flags': header['flags'],
            'area_id': header.get('layer_texture_id', 0),  # In retail, area_id is stored in layer_texture_id
            'holes': header['holes'],
            'position': header['position'],
            'liquid_type': header['liquid_type'],
            'has_mcvt': self.MCVT_CHUNK in subchunks,
            'has_mcnr': self.MCNR_CHUNK in subchunks,
            'has_mclq': self.MCLQ_CHUNK in subchunks,
            'x': header['index_x'],
            'y': header['index_y']
        }

        # Add processed subchunk data
        if 'heights' in processed_subchunks:
            mcnk_data['heights'] = processed_subchunks['heights']
        if 'layers' in processed_subchunks:
            mcnk_data['layers'] = processed_subchunks['layers']

        # Add raw subchunks for debugging
        mcnk_data['raw_subchunks'] = {
            name.decode('ascii'): {
                'offset': chunk.offset,
                'size': chunk.size
            } for name, chunk in subchunks.items()
        }

        # Create MCNKInfo with processed data
        mcnk_info = MCNKInfo(
            index=header['index_x'] + header['index_y'] * 16,
            x=header['index_x'],
            y=header['index_y'],
            flags=header['flags'],
            area_id=header.get('layer_texture_id', 0),
            holes=header['holes'],
            subchunks=mcnk_data,  # Store the complete data structure
            liquid_type=header['liquid_type'],
            position=header['position'],
            num_layers=header['layers']
        )

        self.logger.debug(f"Created MCNKInfo with flags={mcnk_info.flags}, area_id={mcnk_info.area_id}, x={mcnk_info.x}, y={mcnk_info.y}, subchunks={list(mcnk_data['raw_subchunks'].keys())}")
        return mcnk_info

    def parse_textures(self):
        """Parse Retail format texture information"""
        for chunk in self.find_chunks(self.MTEX_CHUNK):
            data = self.read_chunk(chunk)
            pos = 0
            while pos < len(data):
                name, next_pos = self.read_padded_string(data, pos)
                if name:
                    self._textures.append(TextureInfo(
                        filename=name,
                        flags=0,  # Set by MCLY
                        effect_id=None,  # Set by MCLY
                        is_terrain=True
                    ))
                pos = next_pos

    def parse_models(self):
        """Parse Retail format model information"""
        # Parse M2 models
        for chunk in self.find_chunks(self.MMDX_CHUNK):
            data = self.read_chunk(chunk)
            pos = 0
            while pos < len(data):
                name, next_pos = self.read_padded_string(data, pos)
                if name:
                    self._m2_models.append(name)
                pos = next_pos
        
        # Parse M2 indices
        for chunk in self.find_chunks(self.MMID_CHUNK):
            data = self.read_chunk(chunk)
            count = len(data) // 4
            self._m2_indices.extend(struct.unpack(f'<{count}I', data))
        
        # Parse WMO models
        for chunk in self.find_chunks(self.MWMO_CHUNK):
            data = self.read_chunk(chunk)
            pos = 0
            while pos < len(data):
                name, next_pos = self.read_padded_string(data, pos)
                if name:
                    self._wmo_models.append(name)
                pos = next_pos
        
        # Parse WMO indices
        for chunk in self.find_chunks(self.MWID_CHUNK):
            data = self.read_chunk(chunk)
            count = len(data) // 4
            self._wmo_indices.extend(struct.unpack(f'<{count}I', data))

    def parse_model_placements(self):
        """Parse Retail format model placement information"""
        # Parse M2 placements
        for chunk in self.find_chunks(self.MDDF_CHUNK):
            data = self.read_chunk(chunk)
            pos = 0
            while pos + 36 <= len(data):
                placement = self._parse_model_placement(data[pos:pos+36], True)
                if placement.name_id < len(self._m2_models):
                    placement.name = self._m2_models[placement.name_id]
                self._m2_placements.append(placement)
                pos += 36
        
        # Parse WMO placements
        for chunk in self.find_chunks(self.MODF_CHUNK):
            data = self.read_chunk(chunk)
            pos = 0
            while pos + 64 <= len(data):
                placement = self._parse_model_placement(data[pos:pos+64], False)
                if placement.name_id < len(self._wmo_models):
                    placement.name = self._wmo_models[placement.name_id]
                self._wmo_placements.append(placement)
                pos += 64

    def validate(self) -> bool:
        """Validate Retail format specific requirements"""
        if not super().validate():
            return False
            
        # Check for required chunks
        if not self.has_chunk(self.MTEX_CHUNK):
            self.logger.warning("Missing MTEX chunk")
            
        # Validate model references
        if self._m2_placements:
            missing_models = [p.name_id for p in self._m2_placements 
                            if p.name_id >= len(self._m2_models)]
            if missing_models:
                self.logger.error(f"Invalid M2 model references: {missing_models}")
                return False
                
        if self._wmo_placements:
            missing_models = [p.name_id for p in self._wmo_placements 
                            if p.name_id >= len(self._wmo_models)]
            if missing_models:
                self.logger.error(f"Invalid WMO model references: {missing_models}")
                return False
                
        return True

    def parse(self) -> Dict[str, any]:
        """Parse Retail format ADT file"""
        # Parse base data first
        result = super().parse()
        
        # Add Retail-specific data
        result.update({
            'format': 'RETAIL',
            'model_indices': {
                'm2': self._m2_indices,
                'wmo': self._wmo_indices
            }
        })
        
        return result