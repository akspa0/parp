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
    MCNKInfo, MCNKFlags, Vector3D, CAaBox
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
            if len(data) != 36:
                raise ChunkError("Invalid MDDF entry size")
                
            name_id, unique_id = struct.unpack('<2I', data[0:8])
            position = Vector3D.unpack(data[8:20])
            rotation = Vector3D.unpack(data[20:32])
            scale = struct.unpack('<f', data[32:36])[0]
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
            
            # Parse MCNK chunks
            for chunk in self.find_chunks(self.MCNK):
                data = self.read_chunk(chunk)
                try:
                    mcnk = self._parse_mcnk_header(data)
                    self._mcnk_info[(mcnk.index_x, mcnk.index_y)] = mcnk
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
                subchunks={}  # We'll handle subchunks separately if needed
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