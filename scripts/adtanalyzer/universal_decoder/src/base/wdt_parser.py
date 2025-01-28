import struct
from typing import Dict, List, Optional, Tuple, Generator
from dataclasses import dataclass
from .chunk_parser import ChunkParser, ChunkInfo, ChunkParsingError
from ..format_detector import FileFormat

@dataclass
class MapTile:
    """Information about a map tile"""
    x: int
    y: int
    flags: int
    async_id: int
    has_data: bool
    data_offset: int
    data_size: int

@dataclass
class ModelReference:
    """Information about a model reference"""
    name: str
    flags: int
    unique_id: int
    position: Tuple[float, float, float]
    rotation: Tuple[float, float, float]
    scale: float

class WDTParserBase(ChunkParser):
    """Base class for WDT file parsing"""

    # Common chunk names
    MVER_CHUNK = b'MVER'  # Version information
    MPHD_CHUNK = b'MPHD'  # Map header
    MAIN_CHUNK = b'MAIN'  # Main array of map tiles
    
    def __init__(self, file_path: str, file_format: FileFormat, reversed_chunks: bool = False):
        super().__init__(file_path, file_format, reversed_chunks)
        self._version: Optional[int] = None
        self._flags: Optional[int] = None
        self._tiles: Dict[Tuple[int, int], MapTile] = {}
        
    @property
    def version(self) -> int:
        """Get WDT version, parsing if necessary"""
        if self._version is None:
            self._parse_version()
        return self._version

    @property
    def flags(self) -> int:
        """Get WDT flags, parsing if necessary"""
        if self._flags is None:
            self._parse_header()
        return self._flags

    def _parse_version(self):
        """Parse MVER chunk to get file version"""
        try:
            chunk = next(self.find_chunks(self.MVER_CHUNK))
            data = self.read_chunk(chunk)
            self._version = struct.unpack('<I', data[:4])[0]
            self.logger.info(f"WDT Version: {self._version}")
        except StopIteration:
            self.logger.warning("No MVER chunk found, assuming version 0")
            self._version = 0
        except Exception as e:
            self.logger.error(f"Error parsing MVER chunk: {e}")
            raise ChunkParsingError("Failed to parse version information") from e

    def _parse_header(self):
        """Parse MPHD chunk to get map flags"""
        try:
            chunk = next(self.find_chunks(self.MPHD_CHUNK))
            data = self.read_chunk(chunk)
            self._flags = struct.unpack('<I', data[:4])[0]
            self.logger.info(f"Map Flags: {self._flags:#x}")
        except StopIteration:
            self.logger.warning("No MPHD chunk found, assuming flags 0")
            self._flags = 0
        except Exception as e:
            self.logger.error(f"Error parsing MPHD chunk: {e}")
            raise ChunkParsingError("Failed to parse map header") from e

    def _parse_main_array(self):
        """Parse MAIN chunk to get map tile information"""
        try:
            chunk = next(self.find_chunks(self.MAIN_CHUNK))
            data = self.read_chunk(chunk)
            
            # MAIN chunk contains 64x64 array of map tile references
            for y in range(64):
                for x in range(64):
                    offset = (y * 64 + x) * 8
                    if offset + 8 > len(data):
                        break
                        
                    flags, async_id = struct.unpack('<II', data[offset:offset+8])
                    has_data = (flags & 0x1) != 0
                    
                    if has_data:
                        self._tiles[(x, y)] = MapTile(
                            x=x,
                            y=y,
                            flags=flags,
                            async_id=async_id,
                            has_data=True,
                            data_offset=0,  # Will be set by format-specific parser
                            data_size=0     # Will be set by format-specific parser
                        )
                        
        except StopIteration:
            self.logger.error("No MAIN chunk found")
            raise ChunkParsingError("Failed to parse map tiles: MAIN chunk missing")
        except Exception as e:
            self.logger.error(f"Error parsing MAIN chunk: {e}")
            raise ChunkParsingError("Failed to parse map tiles") from e

    def get_tile(self, x: int, y: int) -> Optional[MapTile]:
        """Get information about a specific map tile"""
        return self._tiles.get((x, y))

    def iter_tiles(self) -> Generator[MapTile, None, None]:
        """Iterate over all map tiles that have data"""
        yield from self._tiles.values()

    def get_tile_count(self) -> int:
        """Get the number of map tiles that have data"""
        return len(self._tiles)

    def is_global_model(self) -> bool:
        """Check if this is a global WMO map"""
        return bool(self.flags & 0x1)

    def has_mphd(self) -> bool:
        """Check if file has a map header"""
        return self.has_chunk(self.MPHD_CHUNK)

    def validate(self) -> bool:
        """
        Validate the WDT file structure
        
        Returns:
            bool: Whether the file appears valid
        """
        try:
            # Check for required chunks
            if not self.has_chunk(self.MVER_CHUNK):
                self.logger.error("Missing MVER chunk")
                return False
                
            if not self.has_chunk(self.MAIN_CHUNK):
                self.logger.error("Missing MAIN chunk")
                return False
                
            # Version check
            if self.version not in {0, 18}:  # Known good versions
                self.logger.warning(f"Unusual WDT version: {self.version}")
                
            # Basic tile validation
            for tile in self.iter_tiles():
                if tile.x < 0 or tile.x >= 64 or tile.y < 0 or tile.y >= 64:
                    self.logger.error(f"Invalid tile coordinates: ({tile.x}, {tile.y})")
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return False

    def parse(self) -> Dict[str, any]:
        """
        Parse the WDT file and return structured data
        
        This base implementation handles common structures.
        Format-specific parsers should override this to add their own parsing.
        """
        self._parse_version()
        self._parse_header()
        self._parse_main_array()
        
        return {
            'version': self.version,
            'flags': self.flags,
            'is_global_model': self.is_global_model(),
            'tiles': [
                {
                    'x': tile.x,
                    'y': tile.y,
                    'flags': tile.flags,
                    'async_id': tile.async_id,
                    'has_data': tile.has_data,
                    'data_offset': tile.data_offset,
                    'data_size': tile.data_size
                }
                for tile in self.iter_tiles()
            ]
        }