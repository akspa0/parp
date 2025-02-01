"""
WDT (World Definition Table) file parser.
Supports both Retail and Alpha formats.
"""
import struct
from typing import Dict, List, Optional, Set, Tuple, Union
from pathlib import Path

from terrain_parser import TerrainParser, ChunkError, ParsingError
from terrain_structures import (
    WDTFile, MapTile, ModelReference, ModelPlacement, WMOPlacement,
    Vector3D, CAaBox, WDTFlags
)

class WDTParser(TerrainParser):
    """Parser for WDT terrain files"""
    
    def __init__(self, file_path: str):
        """Initialize WDT parser"""
        super().__init__(file_path)
        self._version: Optional[int] = None
        self._flags: Optional[WDTFlags] = None
        self._tiles: Dict[Tuple[int, int], MapTile] = {}
        self._m2_models: List[ModelReference] = []
        self._wmo_models: List[ModelReference] = []
        self._m2_placements: List[ModelPlacement] = []
        self._wmo_placements: List[WMOPlacement] = []
        self._format_type = 'retail'  # Default to retail format
        
    def _parse_version(self) -> int:
        """Parse MVER chunk"""
        for chunk in self.find_chunks(self.MVER):
            data = self.read_chunk(chunk)
            return struct.unpack('<I', data[:4])[0]
        return 18  # Default version if not found
        
    def _parse_header(self, data: bytes) -> WDTFlags:
        """Parse MPHD chunk"""
        if len(data) < 32:
            raise ChunkError("MPHD chunk too small")
            
        flags = struct.unpack('<I', data[0:4])[0]
        return WDTFlags(flags)
        
    def _parse_main_array(self, data: bytes) -> List[MapTile]:
        """Parse MAIN chunk"""
        tiles = []
        entry_size = 8
        for y in range(64):
            for x in range(64):
                offset = (y * 64 + x) * entry_size
                if offset + entry_size > len(data):
                    break
                    
                entry_data = data[offset:offset+entry_size]
                offset, size = struct.unpack('<II', entry_data)
                
                if offset > 0:  # Tile exists
                    tiles.append(MapTile(
                        x=x,
                        y=y,
                        offset=offset,
                        size=size,
                        flags=0,  # Flags not used in MAIN
                        async_id=0  # Async ID not used in MAIN
                    ))
                    
        return tiles
        
    def _parse_model_names(self, data: bytes, is_alpha: bool = False) -> List[ModelReference]:
        """Parse model name chunks (MMDX/MDNM for M2, MWMO/MONM for WMO)"""
        models = []
        offset = 0
        while offset < len(data):
            if data[offset] == 0:  # Skip empty strings
                offset += 1
                continue
            end = data.find(b'\0', offset)
            if end == -1:
                break
            name = data[offset:end].decode('utf-8', errors='replace')
            models.append(ModelReference(
                path=name,
                format_type='alpha' if is_alpha else 'retail',
                name_id=len(models)  # Index becomes the name_id
            ))
            offset = end + 1
        return models
        
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
            
    def parse(self) -> WDTFile:
        """Parse WDT file"""
        try:
            self.open()
            
            # Parse version
            self._version = self._parse_version()
            if self._version != 18:
                self.logger.warning(f"Unexpected WDT version: {self._version}")
            
            # Detect format type based on chunks
            for chunk in self.find_chunks():
                if chunk.name in [b'MDNM', b'MONM']:
                    self._format_type = 'alpha'
                    self.logger.info("Detected Alpha format WDT")
                    break
                elif chunk.name in [b'MMDX', b'MWMO']:
                    self._format_type = 'retail'
                    self.logger.info("Detected Retail format WDT")
                    break
            
            # Parse header flags
            for chunk in self.find_chunks(self.MPHD):
                data = self.read_chunk(chunk)
                self._flags = self._parse_header(data)
            
            # Parse main array (tile references)
            for chunk in self.find_chunks(self.MAIN):
                data = self.read_chunk(chunk)
                for tile in self._parse_main_array(data):
                    self._tiles[(tile.x, tile.y)] = tile
            
            # Parse model names based on format
            if self._format_type == 'alpha':
                # Alpha format uses MDNM/MONM
                for chunk in self.find_chunks(b'MDNM'):
                    data = self.read_chunk(chunk)
                    self._m2_models.extend(self._parse_model_names(data, True))
                    
                for chunk in self.find_chunks(b'MONM'):
                    data = self.read_chunk(chunk)
                    self._wmo_models.extend(self._parse_model_names(data, True))
            else:
                # Retail format uses MMDX/MWMO
                for chunk in self.find_chunks(self.MMDX):
                    data = self.read_chunk(chunk)
                    self._m2_models.extend(self._parse_model_names(data))
                    
                for chunk in self.find_chunks(self.MWMO):
                    data = self.read_chunk(chunk)
                    self._wmo_models.extend(self._parse_model_names(data))
            
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
            
            return WDTFile(
                path=str(self.file_path),
                file_type='wdt',
                format_type=self._format_type,
                version=self._version,
                flags=self._flags or WDTFlags(0),
                map_name=self.file_path.stem,
                chunk_order=self.chunk_order,
                tiles=self._tiles,
                m2_models=self._m2_models,
                wmo_models=self._wmo_models,
                m2_placements=self._m2_placements,
                wmo_placements=self._wmo_placements,
                is_global_wmo=bool(self._flags and WDTFlags.GlobalWMO in self._flags)
            )
            
        finally:
            self.close()
            
    def validate(self) -> bool:
        """Validate WDT file structure"""
        try:
            self.open()
            
            # Check for required chunks
            required_chunks = {self.MVER, self.MPHD, self.MAIN}
            found_chunks = {chunk.name for chunk in self.find_chunks()}
            
            if not required_chunks.issubset(found_chunks):
                missing = required_chunks - found_chunks
                self.logger.error(f"Missing required chunks: {missing}")
                return False
                
            # Verify version
            if self._version is None:
                self._version = self._parse_version()
            if self._version != 18:
                self.logger.warning(f"Unexpected WDT version: {self._version}")
                
            # Check MAIN array size
            for chunk in self.find_chunks(self.MAIN):
                if chunk.size != 64 * 64 * 8:  # 64x64 grid, 8 bytes per entry
                    self.logger.error(f"Invalid MAIN chunk size: {chunk.size}")
                    return False
                break
                
            return True
            
        except (ParsingError, ChunkError) as e:
            self.logger.error(f"Validation failed: {e}")
            return False
            
        finally:
            self.close()