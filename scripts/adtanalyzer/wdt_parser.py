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
    Vector3D, CAaBox, WDTFlags, ChunkInfo
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
        self._chunk_offsets: Dict[str, ChunkInfo] = {}  # Track chunk offsets
        
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
        
    def _read_tile_data(self, offset: int, size: int) -> Tuple[bytes, bytes]:
        """Read tile data from WDT file"""
        self._file.seek(offset)
        
        # Read MTEX chunk header
        mtex_name = self._file.read(4)[::-1] if self.reverse_names else self._file.read(4)
        if mtex_name != b'MTEX':
            raise ChunkError(f"Expected MTEX chunk, got {mtex_name}")
        mtex_size = struct.unpack('<I', self._file.read(4))[0]
        mtex_data = self._file.read(mtex_size)
        
        # Read MCNK chunk header
        mcnk_name = self._file.read(4)[::-1] if self.reverse_names else self._file.read(4)
        if mcnk_name != b'MCNK':
            raise ChunkError(f"Expected MCNK chunk, got {mcnk_name}")
        mcnk_size = struct.unpack('<I', self._file.read(4))[0]
        mcnk_data = self._file.read(mcnk_size)
        
        return mtex_data, mcnk_data

    def _create_adt_file(self, x: int, y: int, mtex_data: bytes, mcnk_data: bytes) -> bytes:
        """Create ADT file from tile data"""
        # Create ADT header (MVER chunk)
        mver = b'REVM' if self.reverse_names else b'MVER'
        mver_data = struct.pack('<I', 18)  # Version 18
        mver_chunk = mver + struct.pack('<I', len(mver_data)) + mver_data
        
        # Create MTEX chunk
        mtex = b'XETM' if self.reverse_names else b'MTEX'
        mtex_chunk = mtex + struct.pack('<I', len(mtex_data)) + mtex_data
        
        # Create MCNK chunk
        mcnk = b'KNCM' if self.reverse_names else b'MCNK'
        mcnk_chunk = mcnk + struct.pack('<I', len(mcnk_data)) + mcnk_data
        
        # Combine all chunks
        return mver_chunk + mtex_chunk + mcnk_chunk

    def _parse_main_array(self, data: bytes, is_alpha: bool = False) -> Dict[Tuple[int, int], MapTile]:
        """Parse MAIN chunk"""
        tiles = {}
        entry_size = 16 if is_alpha else 8  # Alpha format uses 16-byte entries
        
        for y in range(64):
            for x in range(64):
                offset = (y * 64 + x) * entry_size
                if offset + entry_size > len(data):
                    break
                    
                entry_data = data[offset:offset+entry_size]
                if is_alpha:
                    # Alpha format: 16 bytes (offset, size, flags, async_id)
                    offset, size, flags, async_id = struct.unpack('<4I', entry_data)
                    
                    # Decode Alpha format flags
                    has_adt = bool(flags & 0x1)
                    loaded = bool(flags & 0x2)
                    has_mccv = bool(flags & 0x8)
                    has_big_alpha = bool(flags & 0x10)
                    has_terrain = bool(flags & 0x20)
                    has_vertex_colors = bool(flags & 0x40)
                    
                    if has_adt and offset > 0:
                        try:
                            # Read tile data
                            mtex_data, mcnk_data = self._read_tile_data(offset, size)
                            
                            # Create ADT file content
                            adt_data = self._create_adt_file(x, y, mtex_data, mcnk_data)
                            
                            self.logger.debug(
                                f"Alpha format tile at ({x}, {y}): "
                                f"MTEX size: {len(mtex_data)}, "
                                f"MCNK size: {len(mcnk_data)}, "
                                f"flags: terrain={has_terrain}, colors={has_vertex_colors}"
                            )
                            
                            tiles[(x, y)] = MapTile(
                                x=x,
                                y=y,
                                offset=offset,
                                size=size,
                                flags=flags,
                                async_id=async_id,
                                mcnk_data={
                                    'adt_data': adt_data,
                                    'has_terrain': has_terrain,
                                    'has_vertex_colors': has_vertex_colors,
                                    'has_big_alpha': has_big_alpha
                                }
                            )
                        except Exception as e:
                            self.logger.warning(f"Failed to read tile data at ({x}, {y}): {e}")
                else:
                    # Retail format: 8 bytes (offset, size)
                    offset, size = struct.unpack('<II', entry_data)
                    if offset > 0:  # Tile exists
                        tiles[(x, y)] = MapTile(
                            x=x,
                            y=y,
                            offset=offset,
                            size=size,
                            flags=0,
                            async_id=0,
                            mcnk_data=None
                        )
                    
        return tiles
        
    def _parse_model_names(self, data: bytes, is_alpha: bool = False) -> List[ModelReference]:
        """Parse model name chunks (MMDX/MDNM for M2, MWMO/MONM for WMO)"""
        models = []
        max_name_length = 260  # Maximum reasonable path length
        
        # Split data on null bytes for both formats
        names = [name for name in data.split(b'\0') if name]
        
        for i, name_bytes in enumerate(names):
            try:
                if len(name_bytes) > max_name_length:
                    self.logger.warning(f"Model name too long ({len(name_bytes)} bytes) at index {i}")
                    continue
                
                name = name_bytes.decode('utf-8', errors='replace')
                
                # Basic validation of model path
                if not name or not any(name.endswith(ext) for ext in ['.m2', '.mdx', '.wmo']):
                    self.logger.warning(f"Suspicious model name: {name}")
                    continue
                
                # In Alpha format, the index is used directly as name_id
                # In Retail format, we need to handle potential MMID/MWID indices
                models.append(ModelReference(
                    path=name,
                    format_type='alpha' if is_alpha else 'retail',
                    name_id=i  # Direct index in Alpha format
                ))
                self.logger.debug(f"Found model: {name} (id: {i})")
                
            except UnicodeDecodeError as e:
                self.logger.warning(f"Failed to decode model name at index {i}: {e}")
                continue
        
        if not models:
            self.logger.warning("No valid model names found in chunk")
        else:
            self.logger.info(f"Parsed {len(models)} model names")
            
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
            
            placement = WMOPlacement(
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
            
            return placement
            
        else:
            entry_size = 36 if self._format_type == 'alpha' else 40
            if len(data) != entry_size:
                raise ChunkError(f"Invalid MDDF entry size for {self._format_type} format")
                
            name_id, unique_id = struct.unpack('<2I', data[0:8])
            position = Vector3D.unpack(data[8:20])
            rotation = Vector3D.unpack(data[20:32])
            
            if self._format_type == 'alpha':
                # Alpha format: 36 bytes, scale and flags are 2 bytes each
                scale, flags = struct.unpack('<HH', data[32:36])
                scale = scale / 1024.0  # Convert to float
            else:
                # Retail format: 40 bytes, scale is float, flags is uint32
                scale = struct.unpack('<f', data[32:36])[0]
                flags = struct.unpack('<I', data[36:40])[0]
            
            placement = ModelPlacement(
                name_id=name_id,
                unique_id=unique_id,
                position=position,
                rotation=rotation,
                scale=scale/1024.0,
                flags=flags
            )
            
            return placement
            
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
            
            # Track all chunk offsets first
            self._chunk_offsets.clear()  # Reset offsets
            for chunk in self.find_chunks():
                chunk_name = chunk.name.decode('ascii', errors='replace')
                self._chunk_offsets[chunk_name] = ChunkInfo(
                    name=chunk.name,
                    offset=chunk.offset,
                    size=chunk.size,
                    data_offset=chunk.data_offset
                )
                self.logger.debug(f"Found chunk {chunk_name} at offset {chunk.offset}, size {chunk.size}")
                
            # Parse main array (tile references)
            for chunk in self.find_chunks(self.MAIN):
                data = self.read_chunk(chunk)
                self._tiles = self._parse_main_array(data, self._format_type == 'alpha')
                for (x, y), tile in self._tiles.items():
                    self.logger.debug(f"Found valid tile at {x},{y} (offset: {tile.offset}, size: {tile.size})")
                    if self._format_type == 'alpha' and tile.mcnk_data:
                        self.logger.debug(f"Alpha format tile at ({x}, {y}) with ADT data size: {len(tile.mcnk_data['adt_data'])}")
            
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
                entry_size = 36 if self._format_type == 'alpha' else 40  # Format-specific entry size
                # Validate chunk size is multiple of entry size
                if len(data) % entry_size != 0:
                    self.logger.warning(f"MDDF chunk size {len(data)} is not a multiple of entry size {entry_size}")
                    # Adjust data to include only complete entries
                    data = data[:(len(data) // entry_size) * entry_size]
                
                # Process entries
                entry_count = len(data) // entry_size
                for i in range(entry_count):
                    entry_start = i * entry_size
                    entry = data[entry_start:entry_start + entry_size]
                    
                    try:
                        placement = self._parse_model_placement(entry)
                        # Handle model references based on format
                        if self._format_type == 'alpha':
                            # In Alpha format, name_ids are direct indices
                            if placement.name_id < len(self._m2_models):
                                self._m2_placements.append(placement)
                            else:
                                self.logger.warning(f"Skipping Alpha MDDF entry with invalid name_id: {placement.name_id} (max: {len(self._m2_models)-1})")
                        else:
                            # In Retail format, validate against reasonable limits
                            if placement.name_id > 1000000:
                                self.logger.warning(f"Suspiciously large name_id in MDDF entry: {placement.name_id}")
                                continue
                            if placement.name_id < len(self._m2_models):
                                self._m2_placements.append(placement)
                            else:
                                self.logger.warning(f"Skipping Retail MDDF entry with invalid name_id: {placement.name_id} (max: {len(self._m2_models)-1})")
                    except (ChunkError, struct.error) as e:
                        self.logger.warning(f"Failed to parse MDDF entry at offset {entry_start}: {e}")
            
            for chunk in self.find_chunks(self.MODF):
                data = self.read_chunk(chunk)
                entry_size = 64
                # Validate chunk size is multiple of entry size
                if len(data) % entry_size != 0:
                    self.logger.warning(f"MODF chunk size {len(data)} is not a multiple of entry size {entry_size}")
                    # Adjust data to include only complete entries
                    data = data[:(len(data) // entry_size) * entry_size]
                
                # Process entries
                entry_count = len(data) // entry_size
                for i in range(entry_count):
                    entry_start = i * entry_size
                    entry = data[entry_start:entry_start + entry_size]
                    
                    try:
                        placement = self._parse_model_placement(entry, is_wmo=True)
                        # Handle model references based on format
                        if self._format_type == 'alpha':
                            # In Alpha format, name_ids are direct indices
                            if placement.name_id < len(self._wmo_models):
                                self._wmo_placements.append(placement)
                            else:
                                self.logger.warning(f"Skipping Alpha MODF entry with invalid name_id: {placement.name_id} (max: {len(self._wmo_models)-1})")
                        else:
                            # In Retail format, validate against reasonable limits
                            if placement.name_id > 1000000:
                                self.logger.warning(f"Suspiciously large name_id in MODF entry: {placement.name_id}")
                                continue
                            if placement.name_id < len(self._wmo_models):
                                self._wmo_placements.append(placement)
                            else:
                                self.logger.warning(f"Skipping Retail MODF entry with invalid name_id: {placement.name_id} (max: {len(self._wmo_models)-1})")
                    except (ChunkError, struct.error) as e:
                        self.logger.warning(f"Failed to parse MODF entry at offset {entry_start}: {e}")
            
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
                is_global_wmo=bool(self._flags and WDTFlags.GlobalWMO in self._flags),
                chunk_offsets=self._chunk_offsets
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
                
            # Check MAIN array size based on format
            for chunk in self.find_chunks(self.MAIN):
                expected_size = 64 * 64 * (16 if self._format_type == 'alpha' else 8)
                if chunk.size != expected_size:
                    self.logger.error(
                        f"Invalid MAIN chunk size for {self._format_type} format. "
                        f"Expected {expected_size}, got {chunk.size}"
                    )
                    return False
                break
                
            return True
            
        except (ParsingError, ChunkError) as e:
            self.logger.error(f"Validation failed: {e}")
            return False
            
        finally:
            self.close()