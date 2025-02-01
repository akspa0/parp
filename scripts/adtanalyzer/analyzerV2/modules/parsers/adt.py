"""
ADT (Area Definition Table) file parser.
Handles both retail and alpha format ADT files.
"""
import struct
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseParser, ChunkError
from ..models import (
    Vector3D, MCNKFlags,
    TextureInfo, TextureLayer,
    ModelPlacement, WMOPlacement,
    MCNKInfo, ADTFile
)
from ..utils.binary import (
    read_packed_float, read_packed_int, read_packed_uint,
    read_packed_string, read_packed_vec3
)

class ADTParser(BaseParser):
    """Parser for ADT terrain files"""
    
    def __init__(self, file_path: Path):
        super().__init__(file_path)
        self.version = 0
        self.flags = MCNKFlags(0)
        self.textures: List[TextureInfo] = []
        self.m2_models: List[str] = []
        self.wmo_models: List[str] = []
        self.m2_placements: List[ModelPlacement] = []
        self.wmo_placements: List[WMOPlacement] = []
        self.mcnk_chunks: Dict[Tuple[int, int], MCNKInfo] = {}
        self.subchunks: Dict[Tuple[int, int], Dict[str, Dict]] = {}
        
    def parse(self) -> ADTFile:
        """Parse ADT file"""
        try:
            self.open()
            chunks = self.parse_chunks()
            
            # Extract map name from path
            map_name = self.path.stem
            if '_' in map_name:
                map_name = map_name.split('_')[0]
            
            return ADTFile(
                path=self.path,
                file_type='adt',
                format_type='retail' if self.version >= 18 else 'alpha',
                version=self.version,
                flags=self.flags,
                map_name=map_name,
                chunk_order=self._chunk_order,
                textures=self.textures,
                m2_models=self.m2_models,
                wmo_models=self.wmo_models,
                m2_placements=self.m2_placements,
                wmo_placements=self.wmo_placements,
                mcnk_chunks=self.mcnk_chunks,
                subchunks=self.subchunks
            )
            
        finally:
            self.close()
            
    def parse_chunk(self, chunk_name: str, size: int) -> Any:
        """Parse ADT chunk"""
        chunk_start = self.tell()
        
        try:
            if chunk_name == 'MVER':
                self.version = self.read_struct('<I')[0]
                return self.version
                
            elif chunk_name == 'MHDR':
                flags = self.read_struct('<I')[0]
                self.flags = MCNKFlags(flags)
                self.skip_chunk(size - 4)  # Skip remaining header data
                return flags
                
            elif chunk_name == 'MTEX':
                # Read texture filenames
                data = self.read_bytes(size)
                offset = 0
                while offset < size:
                    filename, read = read_packed_string(data, offset)
                    if not filename:
                        break
                    self.textures.append(TextureInfo(filename=filename))
                    offset += read
                return self.textures
                
            elif chunk_name == 'MMDX':
                # Read M2 model filenames
                data = self.read_bytes(size)
                offset = 0
                while offset < size:
                    filename, read = read_packed_string(data, offset)
                    if not filename:
                        break
                    self.m2_models.append(filename)
                    offset += read
                return self.m2_models
                
            elif chunk_name == 'MWMO':
                # Read WMO model filenames
                data = self.read_bytes(size)
                offset = 0
                while offset < size:
                    filename, read = read_packed_string(data, offset)
                    if not filename:
                        break
                    self.wmo_models.append(filename)
                    offset += read
                return self.wmo_models
                
            elif chunk_name == 'MDDF':
                # Read M2 placements
                count = size // 36
                for _ in range(count):
                    name_id, = self.read_struct('<I')
                    unique_id, = self.read_struct('<I')
                    pos = Vector3D(*self.read_struct('<3f'))
                    rot = Vector3D(*self.read_struct('<3f'))
                    scale, = self.read_struct('<H')
                    flags, = self.read_struct('<H')
                    
                    self.m2_placements.append(ModelPlacement(
                        name_id=name_id,
                        unique_id=unique_id,
                        position=pos,
                        rotation=rot,
                        scale=scale / 1024.0,
                        flags=flags
                    ))
                return self.m2_placements
                
            elif chunk_name == 'MODF':
                # Read WMO placements
                count = size // 64
                for _ in range(count):
                    name_id, = self.read_struct('<I')
                    unique_id, = self.read_struct('<I')
                    pos = Vector3D(*self.read_struct('<3f'))
                    rot = Vector3D(*self.read_struct('<3f'))
                    bounds_min = Vector3D(*self.read_struct('<3f'))
                    bounds_max = Vector3D(*self.read_struct('<3f'))
                    flags, = self.read_struct('<H')
                    doodad_set, = self.read_struct('<H')
                    name_set, = self.read_struct('<H')
                    scale, = self.read_struct('<H')
                    
                    self.wmo_placements.append(WMOPlacement(
                        name_id=name_id,
                        unique_id=unique_id,
                        position=pos,
                        rotation=rot,
                        scale=scale / 1024.0,
                        flags=flags,
                        doodad_set=doodad_set,
                        name_set=name_set,
                        bounding_box=CAaBox(min=bounds_min, max=bounds_max)
                    ))
                return self.wmo_placements
                
            elif chunk_name == 'MCNK':
                # Parse MCNK header
                flags = MCNKFlags(self.read_struct('<I')[0])
                index_x = self.read_struct('<I')[0]
                index_y = self.read_struct('<I')[0]
                n_layers = self.read_struct('<I')[0]
                n_doodad_refs = self.read_struct('<I')[0]
                height_offset = self.read_struct('<I')[0]
                height_layers = self.read_struct('<I')[0]
                height_mdt = self.read_struct('<I')[0]
                holes_low = self.read_struct('<I')[0]
                unknown1 = self.read_struct('<I')[0]
                unknown2 = self.read_struct('<I')[0]
                unknown3 = self.read_struct('<I')[0]
                predTex = self.read_struct('<I')[0]
                noEffectDoodad = self.read_struct('<I')[0]
                unknown4 = self.read_struct('<I')[0]
                holes_high = self.read_struct('<I')[0]
                unknown5 = self.read_struct('<I')[0]
                unknown6 = self.read_struct('<I')[0]
                unknown7 = self.read_struct('<I')[0]
                unknown8 = self.read_struct('<I')[0]
                
                # Create MCNK info
                mcnk = MCNKInfo(
                    flags=flags,
                    index_x=index_x,
                    index_y=index_y,
                    n_layers=n_layers,
                    n_doodad_refs=n_doodad_refs,
                    position=Vector3D(0, 0, 0),  # Will be set from MCVT
                    area_id=0,  # Will be set from MCNR
                    holes=holes_low,
                    layer_flags=0,  # Will be set from MCLY
                    render_flags=0,
                    has_layer_height=bool(height_layers),
                    min_elevation=0,  # Will be set from MCVT
                    max_elevation=0,  # Will be set from MCVT
                    liquid_type=0,  # Will be set from MCLQ
                    predTex=predTex,
                    noEffectDoodad=noEffectDoodad,
                    holes_high_res=holes_high
                )
                
                # Store chunk info
                coord = (index_x, index_y)
                self.mcnk_chunks[coord] = mcnk
                self.subchunks[coord] = {}
                
                # Parse subchunks
                subchunk_end = chunk_start + size
                while self.tell() < subchunk_end:
                    try:
                        name, subsize = self.read_chunk_header()
                        self.subchunks[coord][name] = {
                            'offset': self.tell(),
                            'size': subsize,
                            'data_offset': self.tell() - chunk_start
                        }
                        self.skip_chunk(subsize)
                    except EOFError:
                        break
                        
                return mcnk
                
            else:
                # Skip unknown chunks
                self.skip_chunk(size)
                return None
                
        except Exception as e:
            raise ChunkError(f"Error parsing chunk {chunk_name}: {e}")
            
        finally:
            # Ensure we're at the end of the chunk
            chunk_end = chunk_start + size + 8  # Include header size
            if self.tell() != chunk_end:
                self.seek(chunk_end)