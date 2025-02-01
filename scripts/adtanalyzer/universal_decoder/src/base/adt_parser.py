import struct
from typing import Dict, List, Optional, Tuple, Generator, Set
from dataclasses import dataclass
from .chunk_parser import ChunkParser, ChunkInfo, ChunkParsingError
from ..format_detector import FileFormat

@dataclass
class MCNKInfo:
    """Information about an MCNK (map chunk) and its subchunks"""
    index: int
    x: int
    y: int
    flags: int
    area_id: int
    holes: int
    subchunks: Dict[bytes, ChunkInfo]
    liquid_type: int
    position: Tuple[float, float, float]
    num_layers: int

@dataclass
class TextureInfo:
    """Information about a texture layer"""
    filename: str
    flags: int
    effect_id: Optional[int] = None
    is_terrain: bool = True

@dataclass
class ModelPlacement:
    """Information about a placed model (M2 or WMO)"""
    name_id: int
    unique_id: int
    position: Tuple[float, float, float]
    rotation: Tuple[float, float, float]
    scale: float
    flags: int

class ADTParserBase(ChunkParser):
    """Base class for ADT file parsing"""

    # Common chunk names
    MVER_CHUNK = b'MVER'  # Version information
    MHDR_CHUNK = b'MHDR'  # ADT header
    MCNK_CHUNK = b'MCNK'  # Map chunk
    MTEX_CHUNK = b'MTEX'  # Texture filenames
    MMDX_CHUNK = b'MMDX'  # M2 model filenames
    MMID_CHUNK = b'MMID'  # M2 model indices
    MWMO_CHUNK = b'MWMO'  # WMO model filenames
    MWID_CHUNK = b'MWID'  # WMO model indices
    MDDF_CHUNK = b'MDDF'  # M2 model placements
    MODF_CHUNK = b'MODF'  # WMO model placements
    
    # MCNK subchunk names
    MCVT_CHUNK = b'MCVT'  # Height map
    MCNR_CHUNK = b'MCNR'  # Normals
    MCLY_CHUNK = b'MCLY'  # Texture layers
    MCRF_CHUNK = b'MCRF'  # Reference list
    MCSH_CHUNK = b'MCSH'  # Shadow map
    MCAL_CHUNK = b'MCAL'  # Alpha maps
    MCLQ_CHUNK = b'MCLQ'  # Liquid data
    MCSE_CHUNK = b'MCSE'  # Sound emitters

    def __init__(self, file_path: str, file_format: FileFormat, reversed_chunks: bool = False):
        super().__init__(file_path, file_format, reversed_chunks)
        self._version: Optional[int] = None
        self._flags: Optional[int] = None
        self._mcnk_chunks: Dict[int, MCNKInfo] = {}
        self._textures: List[TextureInfo] = []
        self._m2_models: List[str] = []
        self._wmo_models: List[str] = []
        self._m2_placements: List[ModelPlacement] = []
        self._wmo_placements: List[ModelPlacement] = []

    @property
    def version(self) -> int:
        """Get ADT version, parsing if necessary"""
        if self._version is None:
            self._parse_version()
        return self._version

    def _parse_version(self):
        """Parse MVER chunk to get file version"""
        try:
            chunk = next(self.find_chunks(self.MVER_CHUNK))
            data = self.read_chunk(chunk)
            self._version = struct.unpack('<I', data[:4])[0]
            self.logger.info(f"ADT Version: {self._version}")
        except StopIteration:
            self.logger.warning("No MVER chunk found, assuming version 0")
            self._version = 0
        except Exception as e:
            self.logger.error(f"Error parsing MVER chunk: {e}")
            raise ChunkParsingError("Failed to parse version information") from e

    def _parse_mcnk_header(self, data: bytes) -> Dict[str, any]:
        """Parse MCNK header structure"""
        if len(data) < 128:  # Minimum header size
            raise ChunkParsingError("MCNK header too small")
            
        # Common fields between Alpha and Retail
        flags = struct.unpack('<I', data[0:4])[0]
        ix = struct.unpack('<I', data[4:8])[0]
        iy = struct.unpack('<I', data[8:12])[0]
        layers = struct.unpack('<I', data[12:16])[0]
        doodad_refs = struct.unpack('<I', data[16:20])[0]
        
        # Position data
        pos_x, pos_y, pos_z = struct.unpack('<fff', data[20:32])
        
        # Additional fields may be parsed differently by format-specific implementations
        return {
            'flags': flags,
            'index_x': ix,
            'index_y': iy,
            'num_layers': layers,
            'num_doodad_refs': doodad_refs,
            'position': (pos_x, pos_y, pos_z)
        }

    def _find_mcnk_subchunks(self, mcnk_data: bytes) -> Dict[bytes, ChunkInfo]:
        """Find all subchunks within an MCNK chunk"""
        subchunks = {}
        pos = 128  # Skip MCNK header
        
        while pos + 8 <= len(mcnk_data):
            name = mcnk_data[pos:pos+4]
            if self.reversed_chunks:
                name = name[::-1]
                
            size = struct.unpack('<I', mcnk_data[pos+4:pos+8])[0]
            
            if pos + 8 + size > len(mcnk_data):
                break
                
            subchunks[name] = ChunkInfo(
                name=name,
                offset=pos,
                size=size,
                data_offset=pos + 8,
                format=self.format
            )
            
            pos += 8 + size
            
        return subchunks

    def parse_mcnk(self, chunk: ChunkInfo) -> MCNKInfo:
        """Parse an MCNK chunk and its subchunks"""
        data = self.read_chunk(chunk)
        header = self._parse_mcnk_header(data)
        subchunks = self._find_mcnk_subchunks(data)
        
        return MCNKInfo(
            index=header['index_x'] + header['index_y'] * 16,
            x=header['index_x'],
            y=header['index_y'],
            flags=header['flags'],
            area_id=0,  # Set by format-specific implementation
            holes=0,    # Set by format-specific implementation
            subchunks=subchunks,
            liquid_type=0,  # Set by format-specific implementation
            position=header['position'],
            num_layers=header['num_layers']
        )

    def parse_textures(self):
        """Parse texture information"""
        # Implementation varies by format
        raise NotImplementedError

    def parse_models(self):
        """Parse model information"""
        # Implementation varies by format
        raise NotImplementedError

    def parse_model_placements(self):
        """Parse model placement information"""
        # Implementation varies by format
        raise NotImplementedError

    def get_mcnk(self, x: int, y: int) -> Optional[MCNKInfo]:
        """Get information about a specific map chunk"""
        index = x + y * 16
        return self._mcnk_chunks.get(index)

    def iter_mcnks(self) -> Generator[MCNKInfo, None, None]:
        """Iterate over all map chunks"""
        yield from self._mcnk_chunks.values()

    def validate(self) -> bool:
        """
        Validate the ADT file structure
        
        Returns:
            bool: Whether the file appears valid
        """
        try:
            # Check for required chunks
            if not self.has_chunk(self.MVER_CHUNK):
                self.logger.error("Missing MVER chunk")
                return False
                
            if not self.has_chunk(self.MCNK_CHUNK):
                self.logger.error("Missing MCNK chunks")
                return False
                
            # Version check
            if self.version not in {0, 18}:  # Known good versions
                self.logger.warning(f"Unusual ADT version: {self.version}")
                
            # Basic MCNK validation
            mcnk_indices = {(info.x, info.y) for info in self.iter_mcnks()}
            if len(mcnk_indices) != 256:  # Should have 16x16 chunks
                self.logger.error(f"Invalid number of MCNKs: {len(mcnk_indices)}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return False

    def parse(self) -> Dict[str, any]:
        """
        Parse the ADT file and return structured data
        
        This base implementation handles common structures.
        Format-specific parsers should override this to add their own parsing.
        """
        self._parse_version()
        
        # Parse all MCNK chunks
        mcnk_chunks = list(self.find_chunks(self.MCNK_CHUNK))
        self.logger.debug(f"Found {len(mcnk_chunks)} MCNK chunks")
        
        for chunk in mcnk_chunks:
            try:
                self.logger.debug(f"Processing MCNK chunk at offset {chunk.offset}")
                mcnk = self.parse_mcnk(chunk)
                self._mcnk_chunks[mcnk.index] = mcnk
                self.logger.debug(f"Successfully parsed MCNK chunk {mcnk.index} at ({mcnk.x}, {mcnk.y})")
            except Exception as e:
                self.logger.error(f"Error parsing MCNK at offset {chunk.offset}: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
        
        return {
            'version': self.version,
            'decoded_chunks': {
                'MCNK': [
                    {
                        'flags': mcnk.flags,
                        'area_id': mcnk.area_id,
                        'holes': mcnk.holes,
                        'position': mcnk.position,
                        'liquid_type': mcnk.liquid_type,
                        'flags': mcnk.flags,
                        'area_id': mcnk.area_id,
                        'holes': mcnk.holes,
                        'position': mcnk.position,
                        'liquid_type': mcnk.liquid_type,
                        'x': mcnk.x,
                        'y': mcnk.y,
                        'has_mcvt': mcnk.subchunks.get('has_mcvt', False),
                        'has_mcnr': mcnk.subchunks.get('has_mcnr', False),
                        'has_mclq': mcnk.subchunks.get('has_mclq', False),
                        'heights': mcnk.subchunks.get('heights', []),
                        'layers': mcnk.subchunks.get('layers', [])
                    }
                    for mcnk in self.iter_mcnks()
                ],
                'textures': self._textures,
                'm2_models': self._m2_models,
                'wmo_models': self._wmo_models,
                'm2_placements': self._m2_placements,
                'wmo_placements': self._wmo_placements
            }
        }