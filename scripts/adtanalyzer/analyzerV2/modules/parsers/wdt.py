"""
WDT (World Definition Table) file parser.
Handles both retail and alpha format WDT files.
"""
import struct
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseParser, ChunkError
from ..models import (
    Vector3D, CAaBox, WDTFlags,
    ModelReference, ModelPlacement, WMOPlacement,
    MapTile, WDTFile
)
from ..utils.binary import (
    read_packed_float, read_packed_int, read_packed_uint,
    read_packed_string, read_packed_vec3
)

class WDTParser(BaseParser):
    """Parser for WDT terrain files"""
    
    def __init__(self, file_path: Path):
        super().__init__(file_path)
        self.version = 0
        self.flags = WDTFlags(0)
        self.tiles: Dict[Tuple[int, int], MapTile] = {}
        self.m2_models: List[ModelReference] = []
        self.wmo_models: List[ModelReference] = []
        self.m2_placements: List[ModelPlacement] = []
        self.wmo_placements: List[WMOPlacement] = []
        self.is_global_wmo = False
        
    def parse(self) -> WDTFile:
        """Parse WDT file"""
        try:
            self.open()
            chunks = self.parse_chunks()
            
            # Extract map name from path
            map_name = self.path.stem
            if '_' in map_name:
                map_name = map_name.split('_')[0]
            
            return WDTFile(
                path=self.path,
                file_type='wdt',
                format_type='retail' if self.version >= 18 else 'alpha',
                version=self.version,
                flags=self.flags,
                map_name=map_name,
                chunk_order=self._chunk_order,
                tiles=self.tiles,
                m2_models=self.m2_models,
                wmo_models=self.wmo_models,
                m2_placements=self.m2_placements,
                wmo_placements=self.wmo_placements,
                is_global_wmo=self.is_global_wmo
            )
            
        finally:
            self.close()
            
    def parse_chunk(self, chunk_name: str, size: int) -> Any:
        """Parse WDT chunk"""
        chunk_start = self.tell()
        
        try:
            if chunk_name == 'MVER':
                self.version = self.read_struct('<I')[0]
                return self.version
                
            elif chunk_name == 'MPHD':
                flags = self.read_struct('<I')[0]
                self.flags = WDTFlags(flags)
                self.skip_chunk(size - 4)  # Skip remaining header data
                return flags
                
            elif chunk_name == 'MAIN':
                # Read map tiles
                tile_count = size // 8  # Each tile is 8 bytes
                for i in range(tile_count):
                    flags, = self.read_struct('<I')
                    async_id, = self.read_struct('<I')
                    
                    if flags != 0:  # Only store non-empty tiles
                        x = i % 64
                        y = i // 64
                        self.tiles[(x, y)] = MapTile(
                            x=x,
                            y=y,
                            flags=flags,
                            async_id=async_id
                        )
                return self.tiles
                
            elif chunk_name == 'MWMO':
                # Read WMO filenames
                data = self.read_bytes(size)
                offset = 0
                while offset < size:
                    filename, read = read_packed_string(data, offset)
                    if not filename:
                        break
                    self.wmo_models.append(ModelReference(
                        path=filename,
                        format_type='retail' if self.version >= 18 else 'alpha'
                    ))
                    offset += read
                return self.wmo_models
                
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
                
            elif chunk_name == 'MMDX':
                # Read M2 filenames
                data = self.read_bytes(size)
                offset = 0
                while offset < size:
                    filename, read = read_packed_string(data, offset)
                    if not filename:
                        break
                    self.m2_models.append(ModelReference(
                        path=filename,
                        format_type='retail' if self.version >= 18 else 'alpha'
                    ))
                    offset += read
                return self.m2_models
                
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