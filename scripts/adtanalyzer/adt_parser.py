"""
ADT (Area Definition Table) file parser.
Supports both Retail and Alpha formats.
"""
import struct
from typing import Dict, List, Optional, Set, Tuple, Union
from pathlib import Path

from terrain_parser import TerrainParser, ChunkError, ParsingError
from terrain_structures import (
    ADTFile, TextureInfo, ModelReference, ModelPlacement, WMOPlacement,
    MCNKInfo, MCNKFlags, Vector3D, CAaBox, TextureLayer
)

class ADTParser(TerrainParser):
    """Parser for ADT terrain files"""
    
    def __init__(self, file_path: str):
        """Initialize ADT parser"""
        super().__init__(file_path)
        self._version: Optional[int] = None
        self._textures: List[TextureInfo] = []
        self._m2_models: List[str] = []
        self._wmo_models: List[str] = []
        self._m2_placements: List[ModelPlacement] = []
        self._wmo_placements: List[WMOPlacement] = []
        self._mcnk_info: Dict[Tuple[int, int], MCNKInfo] = {}
        self._subchunks: Dict[Tuple[int, int], Dict[str, Dict]] = {}
        self._format_type = 'retail'  # Default to retail format
        
    def _parse_version(self) -> int:
        """Parse MVER chunk"""
        for chunk in self.find_chunks(self.MVER):
            data = self.read_chunk(chunk)
            return struct.unpack('<I', data[:4])[0]
        return 18  # Default version if not found
        
    def _parse_texture_names(self, data: bytes) -> List[str]:
        """Parse MTEX chunk data"""
        textures = []
        offset = 0
        while offset < len(data):
            if data[offset] == 0:  # Skip empty strings
                offset += 1
                continue
            end = data.find(b'\0', offset)
            if end == -1:
                break
            name = data[offset:end].decode('utf-8', errors='replace')
            textures.append(name)
            offset = end + 1
        return textures
        
    def _parse_mcnk_header(self, data: bytes) -> MCNKInfo:
        """Parse MCNK chunk header"""
        if len(data) < 128:
            raise ChunkError("MCNK header too small")
            
        flags = MCNKFlags(struct.unpack('<I', data[0:4])[0])
        ix, iy = struct.unpack('<2I', data[4:12])
        n_layers, n_refs = struct.unpack('<2I', data[12:20])
        position = Vector3D.unpack(data[20:32])
        area_id, holes = struct.unpack('<2I', data[32:40])
        layer_flags, render_flags = struct.unpack('<2I', data[40:48])
        
        has_height = bool(data[48])
        min_elev, max_elev = struct.unpack('<2f', data[49:57])
        liquid_type = struct.unpack('<I', data[57:61])[0]
        pred_tex, noeff_doodad, holes_high = struct.unpack('<3H', data[61:67])
        
        return MCNKInfo(
            flags=flags,
            index_x=ix,
            index_y=iy,
            n_layers=n_layers,
            n_doodad_refs=n_refs,
            position=position,
            area_id=area_id,
            holes=holes,
            layer_flags=layer_flags,
            render_flags=render_flags,
            has_layer_height=has_height,
            min_elevation=min_elev,
            max_elevation=max_elev,
            liquid_type=liquid_type,
            predTex=pred_tex,
            noEffectDoodad=noeff_doodad,
            holes_high_res=holes_high
        )
        
    def _parse_mcly(self, data: bytes) -> List[TextureLayer]:
        """Parse MCLY (texture layer) chunk"""
        if len(data) < 16:  # Each layer entry is 16 bytes
            raise ChunkError("MCLY chunk too small")
            
        layers = []
        for i in range(0, len(data), 16):
            if i + 16 > len(data):
                break
                
            texture_id, flags, offset_mcal, effect_id = struct.unpack('<4I', data[i:i+16])
            layer = TextureLayer(
                texture_id=texture_id,
                flags=flags,
                offset_mcal=offset_mcal,
                effect_id=effect_id,
                layer_index=len(layers),  # Layer index is order in MCLY
                blend_mode=(flags >> 24) & 0xFF  # Extract blend mode from flags
            )
            layers.append(layer)
            
        return layers
        
    def _parse_mcal(self, data: bytes, layers: List[TextureLayer]):
        """Parse MCAL (alpha map) chunk and assign to layers"""
        current_pos = 0
        for layer in layers:
            if layer.offset_mcal >= len(data):
                continue
                
            # Each alpha map is 64x64 = 4096 bytes
            alpha_size = 4096
            start_pos = layer.offset_mcal
            end_pos = start_pos + alpha_size
            
            if end_pos > len(data):
                break
                
            # Extract alpha values
            alpha_map = list(data[start_pos:end_pos])
            layer.alpha_map = alpha_map
            
    def _parse_mcnr(self, data: bytes) -> List[float]:
        """Parse MCNR (normal data) chunk"""
        if len(data) < 435:  # 145 vertices * 3 bytes
            raise ChunkError("MCNR chunk too small")
            
        normals = []
        for i in range(0, 435, 3):
            # Each normal is stored as 3 signed bytes (-127 to 127)
            x = int.from_bytes(data[i:i+1], byteorder='little', signed=True) / 127.0
            y = int.from_bytes(data[i+1:i+2], byteorder='little', signed=True) / 127.0
            z = int.from_bytes(data[i+2:i+3], byteorder='little', signed=True) / 127.0
            normals.extend([x, y, z])
            
        return normals
        
    def _parse_mcvt(self, data: bytes) -> List[float]:
        """Parse MCVT (height map) chunk"""
        if len(data) < 580:  # 145 vertices * 4 bytes
            raise ChunkError("MCVT chunk too small")
        return list(struct.unpack('<145f', data[:580]))
        
    def _parse_mh2o(self, data: bytes) -> Tuple[List[float], List[int]]:
        """Parse MH2O (liquid) chunk"""
        if len(data) < 8:
            raise ChunkError("MH2O chunk too small")
            
        # Parse header
        flags = struct.unpack('<I', data[0:4])[0]
        type_id = struct.unpack('<I', data[4:8])[0]
        
        # Parse height data
        heights = []
        height_offset = 8
        while height_offset + 4 <= len(data):
            try:
                height = struct.unpack('<f', data[height_offset:height_offset+4])[0]
                heights.append(height)
                height_offset += 4
            except struct.error:
                break
                
        # Parse flags if present
        liquid_flags = []
        if height_offset + 4 <= len(data):
            flags_data = data[height_offset:]
            for i in range(0, len(flags_data), 4):
                if i + 4 > len(flags_data):
                    break
                flag = struct.unpack('<I', flags_data[i:i+4])[0]
                liquid_flags.append(flag)
                
        return heights, liquid_flags
        
    def _parse_model_placement(self, data: bytes, is_wmo: bool = False) -> Union[ModelPlacement, WMOPlacement]:
        """Parse model placement data (MDDF/MODF)"""
        if is_wmo:
            if len(data) != 64:
                raise ChunkError("Invalid MODF entry size")
                
            name_id, unique_id = struct.unpack('<2I', data[0:8])
            position = Vector3D.unpack(data[8:20])
            rotation = Vector3D.unpack(data[20:32])
            
            bounding_box = CAaBox(
                Vector3D.unpack(data[32:44]),  # min
                Vector3D.unpack(data[44:56])   # max
            )
            
            flags, doodad_set, name_set, scale = struct.unpack('<4H', data[56:64])
            
            return WMOPlacement(
                name_id=name_id,
                unique_id=unique_id,
                position=position,
                rotation=rotation,
                scale=scale/1024.0,
                flags=flags,
                doodad_set=doodad_set,
                name_set=name_set,
                bounding_box=bounding_box
            )
        else:
            if len(data) < 36:
                raise ChunkError(f"Invalid MDDF entry size: {len(data)}")
                
            name_id, unique_id = struct.unpack('<2I', data[0:8])
            position = Vector3D.unpack(data[8:20])
            rotation = Vector3D.unpack(data[20:32])
            scale = struct.unpack('<f', data[32:36])[0]
            flags = 0  # Default flags if not present
            if len(data) >= 40:
                flags = struct.unpack('<I', data[36:40])[0]
            
            return ModelPlacement(
                name_id=name_id,
                unique_id=unique_id,
                position=position,
                rotation=rotation,
                scale=scale/1024.0,
                flags=flags
            )
            
    def parse(self) -> ADTFile:
        """Parse ADT file"""
        try:
            self.open()
            
            # Parse version
            self._version = self._parse_version()
            if self._version != 18:
                self.logger.warning(f"Unexpected ADT version: {self._version}")
            
            # Detect format type based on chunks
            for chunk in self.find_chunks():
                if chunk.name in [b'MDNM', b'MONM']:
                    self._format_type = 'alpha'
                    self.logger.info("Detected Alpha format ADT")
                    break
                elif chunk.name in [b'MMDX', b'MWMO']:
                    self._format_type = 'retail'
                    self.logger.info("Detected Retail format ADT")
                    break
            
            # Parse texture names
            for chunk in self.find_chunks(self.MTEX):
                data = self.read_chunk(chunk)
                for name in self._parse_texture_names(data):
                    self._textures.append(TextureInfo(filename=name))
            
            # Parse model names based on format
            if self._format_type == 'alpha':
                # Alpha format uses MDNM/MONM
                for chunk in self.find_chunks(b'MDNM'):
                    data = self.read_chunk(chunk)
                    self._m2_models.extend(self._parse_texture_names(data))
                    
                for chunk in self.find_chunks(b'MONM'):
                    data = self.read_chunk(chunk)
                    self._wmo_models.extend(self._parse_texture_names(data))
            else:
                # Retail format uses MMDX/MWMO
                for chunk in self.find_chunks(self.MMDX):
                    data = self.read_chunk(chunk)
                    self._m2_models.extend(self._parse_texture_names(data))
                    
                for chunk in self.find_chunks(self.MWMO):
                    data = self.read_chunk(chunk)
                    self._wmo_models.extend(self._parse_texture_names(data))
            
            # Parse model placements
            for chunk in self.find_chunks(self.MDDF):
                data = self.read_chunk(chunk)
                entry_size = 36
                for i in range(0, len(data), entry_size):
                    entry = data[i:i+entry_size]
                    if len(entry) == entry_size:
                        try:
                            placement = self._parse_model_placement(entry)
                            self._m2_placements.append(placement)
                        except (ChunkError, struct.error) as e:
                            self.logger.warning(f"Failed to parse MDDF entry: {e}")
            
            for chunk in self.find_chunks(self.MODF):
                data = self.read_chunk(chunk)
                entry_size = 64
                for i in range(0, len(data), entry_size):
                    entry = data[i:i+entry_size]
                    if len(entry) == entry_size:
                        try:
                            placement = self._parse_model_placement(entry, is_wmo=True)
                            self._wmo_placements.append(placement)
                        except (ChunkError, struct.error) as e:
                            self.logger.warning(f"Failed to parse MODF entry: {e}")
            
            # Parse MCNK chunks and store offsets
            for chunk in self.find_chunks(self.MCNK):
                data = self.read_chunk(chunk)
                try:
                    mcnk = self._parse_mcnk_header(data)
                    self._mcnk_info[(mcnk.index_x, mcnk.index_y)] = mcnk
                    
                    # Parse subchunks
                    pos = 128  # Skip header
                    while pos + 8 <= len(data):
                        subchunk_name = data[pos:pos+4]
                        if self.reverse_names:
                            subchunk_name = subchunk_name[::-1]
                        subchunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]
                        
                        if pos + 8 + subchunk_size > len(data):
                            break
                            
                        subchunk_data = data[pos+8:pos+8+subchunk_size]
                        # Store subchunk info in memory
                        if (mcnk.index_x, mcnk.index_y) not in self._subchunks:
                            self._subchunks[(mcnk.index_x, mcnk.index_y)] = {}
                        self._subchunks[(mcnk.index_x, mcnk.index_y)][subchunk_name.decode('ascii')] = {
                            'name': subchunk_name.decode('ascii'),
                            'offset': pos,
                            'size': subchunk_size,
                            'data_offset': pos + 8
                        }
                        
                        # Parse specific subchunks
                        if subchunk_name == b'MCVT':
                            try:
                                heights = self._parse_mcvt(subchunk_data)
                                mcnk.height_map = heights
                            except (ChunkError, struct.error) as e:
                                self.logger.warning(f"Failed to parse MCVT: {e}")
                                
                        elif subchunk_name == b'MH2O':
                            try:
                                heights, flags = self._parse_mh2o(subchunk_data)
                                mcnk.liquid_heights = heights
                                mcnk.liquid_flags = flags
                            except (ChunkError, struct.error) as e:
                                self.logger.warning(f"Failed to parse MH2O: {e}")
                                
                        elif subchunk_name == b'MCLY':
                            try:
                                layers = self._parse_mcly(subchunk_data)
                                mcnk.texture_layers = layers
                            except (ChunkError, struct.error) as e:
                                self.logger.warning(f"Failed to parse MCLY: {e}")
                                
                        elif subchunk_name == b'MCAL':
                            try:
                                if hasattr(mcnk, 'texture_layers') and mcnk.texture_layers:
                                    self._parse_mcal(subchunk_data, mcnk.texture_layers)
                            except (ChunkError, struct.error) as e:
                                self.logger.warning(f"Failed to parse MCAL: {e}")
                                
                        elif subchunk_name == b'MCNR':
                            try:
                                normals = self._parse_mcnr(subchunk_data)
                                mcnk.normal_data = normals
                            except (ChunkError, struct.error) as e:
                                self.logger.warning(f"Failed to parse MCNR: {e}")
                                
                        pos += 8 + subchunk_size
                        
                except (ChunkError, struct.error) as e:
                    self.logger.warning(f"Failed to parse MCNK chunk: {e}")
            
            return ADTFile(
                path=str(self.file_path),
                file_type='adt',
                format_type=self._format_type,
                version=self._version,
                flags=MCNKFlags(0),  # Default flags
                map_name=self.file_path.stem,
                chunk_order=self.chunk_order,
                textures=self._textures,
                m2_models=self._m2_models,
                wmo_models=self._wmo_models,
                m2_placements=self._m2_placements,
                wmo_placements=self._wmo_placements,
                mcnk_chunks=self._mcnk_info,
                subchunks=self._subchunks
            )
            
        finally:
            self.close()
            
    def validate(self) -> bool:
        """Validate ADT file structure"""
        try:
            self.open()
            
            # Check for required chunks
            required_chunks = {self.MVER, self.MHDR, self.MCNK}
            found_chunks = {chunk.name for chunk in self.find_chunks()}
            
            if not required_chunks.issubset(found_chunks):
                missing = required_chunks - found_chunks
                self.logger.error(f"Missing required chunks: {missing}")
                return False
                
            # Verify version
            if self._version is None:
                self._version = self._parse_version()
            if self._version != 18:
                self.logger.warning(f"Unexpected ADT version: {self._version}")
                
            # Check MCNK count
            mcnk_count = sum(1 for _ in self.find_chunks(self.MCNK))
            if mcnk_count != 256:  # 16x16 grid
                self.logger.error(f"Invalid MCNK count: {mcnk_count}")
                return False
                
            return True
            
        except (ParsingError, ChunkError) as e:
            self.logger.error(f"Validation failed: {e}")
            return False
            
        finally:
            self.close()