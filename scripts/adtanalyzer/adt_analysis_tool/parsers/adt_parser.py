"""
ADT (Area Definition Table) file parser.
Implements parsing for WoW ADT file format version 18.
See: https://wowdev.wiki/ADT/v18
"""
import struct
from typing import Dict, List, Optional, Set, Tuple, Union
from pathlib import Path

from ..models.chunks import (
    ADTFile, ChunkHeader, TextureInfo, ModelPlacement, WMOPlacement,
    MCNKInfo, MCNKFlags, MCVTData, MCNRData, MCLYEntry, MCALData,
    MCLQData, MCCVData
)
from ..utils.common_types import (
    Vector2D, Vector3D, Quaternion, CAaBox, RGB, RGBA,
    read_cstring, read_fixed_point, read_packed_bits
)
from .base import BinaryParser, ChunkError, ParsingError

class ADTParser(BinaryParser):
    """Parser for ADT terrain files"""
    
    # Chunk magic constants
    MVER = b'MVER'  # Version
    MHDR = b'MHDR'  # Header
    MCNK = b'MCNK'  # Map chunk
    MTEX = b'MTEX'  # Texture names
    MMDX = b'MMDX'  # M2 model names
    MMID = b'MMID'  # M2 model name indices
    MWMO = b'MWMO'  # WMO model names
    MWID = b'MWID'  # WMO model name indices
    MDDF = b'MDDF'  # M2 placements
    MODF = b'MODF'  # WMO placements
    
    # MCNK subchunk magic constants
    MCVT = b'MCVT'  # Height map
    MCNR = b'MCNR'  # Normals
    MCLY = b'MCLY'  # Layers
    MCRF = b'MCRF'  # References
    MCAL = b'MCAL'  # Alpha maps
    MCSH = b'MCSH'  # Shadows
    MCLQ = b'MCLQ'  # Liquid
    MCSE = b'MCSE'  # Sound emitters
    MCCV = b'MCCV'  # Vertex colors

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
        self._subchunks: Dict[Tuple[int, int], Dict[str, Union[MCVTData, MCNRData, List[MCLYEntry], MCALData, MCLQData, MCCVData]]] = {}

    def _parse_version(self) -> int:
        """Parse MVER chunk"""
        for chunk in self.find_chunks(self.MVER):
            data = self.read_chunk(chunk)
            return struct.unpack('<I', data[:4])[0]
        raise ChunkError("No MVER chunk found")

    def _parse_string_block(self, data: bytes) -> List[str]:
        """Parse block of null-terminated strings"""
        strings = []
        offset = 0
        while offset < len(data):
            string, new_offset = read_cstring(data, offset)
            if string:
                strings.append(string)
            if new_offset <= offset:
                break
            offset = new_offset
        return strings

    def _parse_mcnk_header(self, data: bytes) -> MCNKInfo:
        """Parse MCNK chunk header"""
        if len(data) < 128:
            raise ChunkError("MCNK header too small")
            
        flags = MCNKFlags(struct.unpack('<I', data[0:4])[0])
        ix, iy = struct.unpack('<2I', data[4:12])
        n_layers, n_doodad_refs = struct.unpack('<2I', data[12:20])
        position = Vector3D.unpack(data[20:32])
        area_id, holes = struct.unpack('<2I', data[32:40])
        layer_flags, render_flags = struct.unpack('<2I', data[40:48])
            
        # Parse additional fields
        has_layer_height = bool(data[48])
        min_elev, max_elev = struct.unpack('<2f', data[49:57])
        liquid_type = struct.unpack('<I', data[57:61])[0]
        pred_tex, noeff_doodad, holes_high = struct.unpack('<3H', data[61:67])
            
        return MCNKInfo(
            flags=flags,
            index_x=ix,
            index_y=iy,
            n_layers=n_layers,
            n_doodad_refs=n_doodad_refs,
            position=position,
            area_id=area_id,
            holes=holes,
            layer_flags=layer_flags,
            render_flags=render_flags,
            has_layer_height=has_layer_height,
            min_elevation=min_elev,
            max_elevation=max_elev,
            liquid_type=liquid_type,
            predTex=pred_tex,
            noEffectDoodad=noeff_doodad,
            holes_high_res=holes_high
        )

    def _parse_mcnk_subchunks(self, data: bytes, offset: int = 128) -> Dict[str, Union[MCVTData, MCNRData, List[MCLYEntry], MCALData, MCLQData, MCCVData]]:
        """Parse MCNK subchunks"""
        subchunks = {}
        pos = offset

        while pos + 8 <= len(data):
            magic = data[pos:pos+4]
            size = struct.unpack('<I', data[pos+4:pos+8])[0]
            
            if pos + 8 + size > len(data):
                break
                
            chunk_data = data[pos+8:pos+8+size]
            
            try:
                if magic == self.MCVT:
                    # 145 height values
                    heights = list(struct.unpack('<145f', chunk_data))
                    subchunks['MCVT'] = MCVTData(heights=heights)
                    
                elif magic == self.MCNR:
                    # 145 normal vectors
                    normals = []
                    for i in range(0, len(chunk_data), 3):
                        nx, ny, nz = struct.unpack('<3B', chunk_data[i:i+3])
                        normals.append(Vector3D(
                            nx/127.0 - 1.0,
                            ny/127.0 - 1.0,
                            nz/127.0 - 1.0
                        ))
                    subchunks['MCNR'] = MCNRData(normals=normals)
                    
                elif magic == self.MCLY:
                    # Texture layers
                    layers = []
                    for i in range(0, size, 16):
                        tex_id, flags, offset_mcal, effect_id = struct.unpack('<4I', chunk_data[i:i+16])
                        layers.append(MCLYEntry(
                            texture_id=tex_id,
                            flags=flags,
                            offset_mcal=offset_mcal,
                            effect_id=effect_id
                        ))
                    subchunks['MCLY'] = layers
                    
                elif magic == self.MCAL:
                    # Alpha maps
                    compressed = bool(chunk_data[0] & 0x1) if chunk_data else False
                    subchunks['MCAL'] = MCALData(
                        alpha_map=chunk_data[1:] if compressed else chunk_data,
                        compressed=compressed
                    )
                    
                elif magic == self.MCLQ:
                    # Liquid data
                    if size >= 8:
                        heights = list(struct.unpack('<2f', chunk_data[:8]))
                        flags = list(struct.unpack('<2I', chunk_data[8:16])) if size >= 16 else []
                        subchunks['MCLQ'] = MCLQData(
                            heights=heights,
                            flags=flags,
                            data=chunk_data[16:] if size > 16 else b''
                        )
                        
                elif magic == self.MCCV:
                    # Vertex colors
                    colors = []
                    for i in range(0, min(len(chunk_data), 145*4), 4):
                        r, g, b, a = struct.unpack('<4B', chunk_data[i:i+4])
                        colors.append(RGBA(r, g, b, a))
                    subchunks['MCCV'] = MCCVData(colors=colors)
            
            except struct.error as e:
                self.logger.warning(f"Failed to parse subchunk {magic}: {e}")
            
            pos += 8 + size
            
        return subchunks

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
            scale = read_fixed_point(data[32:36])
            flags = struct.unpack('<I', data[36:40])[0]
             
            return ModelPlacement(
                name_id=name_id,
                unique_id=unique_id,
                position=position,
                rotation=rotation,
                scale=scale,
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
                
            # Parse texture names (MTEX)
            for chunk in self.find_chunks(self.MTEX):
                data = self.read_chunk(chunk)
                self._textures = [TextureInfo(name) for name in self._parse_string_block(data)]
                
            # Parse M2 model names (MMDX + MMID)
            mmdx_data = None
            for chunk in self.find_chunks(self.MMDX):
                mmdx_data = self.read_chunk(chunk)
                break
                
            if mmdx_data:
                for chunk in self.find_chunks(self.MMID):
                    mmid_data = self.read_chunk(chunk)
                    offsets = struct.unpack(f'<{len(mmid_data)//4}I', mmid_data)
                    self._m2_models = self._parse_string_block(mmdx_data)
                    
            # Parse WMO model names (MWMO + MWID)
            mwmo_data = None
            for chunk in self.find_chunks(self.MWMO):
                mwmo_data = self.read_chunk(chunk)
                break
                
            if mwmo_data:
                for chunk in self.find_chunks(self.MWID):
                    mwid_data = self.read_chunk(chunk)
                    offsets = struct.unpack(f'<{len(mwid_data)//4}I', mwid_data)
                    self._wmo_models = self._parse_string_block(mwmo_data)
                    
            # Parse model placements
            for chunk in self.find_chunks(self.MDDF):
                data = self.read_chunk(chunk)
                for i in range(0, len(data), 36):
                    try:
                        placement = self._parse_model_placement(data[i:i+36])
                        self._m2_placements.append(placement)
                    except (ChunkError, struct.error) as e:
                        self.logger.warning(f"Failed to parse MDDF entry: {e}")
                        
            for chunk in self.find_chunks(self.MODF):
                data = self.read_chunk(chunk)
                for i in range(0, len(data), 64):
                    try:
                        placement = self._parse_model_placement(data[i:i+64], is_wmo=True)
                        self._wmo_placements.append(placement)
                    except (ChunkError, struct.error) as e:
                        self.logger.warning(f"Failed to parse MODF entry: {e}")
                        
            # Parse MCNK chunks
            for chunk in self.find_chunks(self.MCNK):
                data = self.read_chunk(chunk)
                try:
                    header = self._parse_mcnk_header(data)
                    subchunks = self._parse_mcnk_subchunks(data)
                    
                    coord = (header.index_x, header.index_y)
                    self._mcnk_info[coord] = header
                    self._subchunks[coord] = subchunks
                    
                except (ChunkError, struct.error) as e:
                    self.logger.warning(f"Failed to parse MCNK chunk: {e}")
                    
            return ADTFile(
                version=self._version,
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
            found_chunks = {chunk.magic for chunk in self.find_chunks()}
            
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