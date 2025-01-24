#!/usr/bin/env python3
from pathlib import Path
import struct
import mmap
from typing import Dict, Iterator, Optional, BinaryIO, List, Union, Tuple
from dataclasses import dataclass
import logging
from enum import IntFlag
import array
import zlib
from collections import defaultdict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ADTHandler")

class ChunkError(Exception):
    """Base exception for chunk processing errors"""
    pass

class MCNKFlags(IntFlag):
    HAS_MCSH = 0x1
    IMPASS = 0x2
    LQ_RIVER = 0x4
    LQ_OCEAN = 0x8
    LQ_MAGMA = 0x10
    LQ_SLIME = 0x20
    HAS_MCCV = 0x40
    UNKNOWN_0x80 = 0x80
    DO_NOT_FIX_ALPHA_MAP = 0x8000
    HIGH_RES_HOLES = 0x10000

@dataclass
class ChunkHeader:
    magic: str
    size: int
    offset: int  # Offset to chunk data start (after header)

@dataclass
class ADTChunkRef:
    """Reference to a chunk within the ADT file"""
    offset: int  # Offset to chunk data
    size: int    # Size of chunk data
    magic: str   # Chunk magic string
    header_offset: int  # Offset to chunk header

    @property
    def data_range(self) -> Tuple[int, int]:
        """Return range of chunk data (start, end)"""
        return (self.offset, self.offset + self.size)

class ADTVersion:
    """Track ADT file version information"""
    def __init__(self, version_data: Optional[bytes] = None):
        self.major = 0
        self.minor = 0
        self.build = 0
        self.revision = 0
        if version_data:
            self.parse(version_data)

    def parse(self, data: bytes) -> None:
        if len(data) >= 16:
            self.major, self.minor, self.build, self.revision = struct.unpack('4I', data[:16])

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.build}.{self.revision}"

    def supports_feature(self, feature: str) -> bool:
        """Check if this version supports a specific feature"""
        # Add version-specific feature checks here
        feature_requirements = {
            'high_res_holes': (self.build >= 18273),  # Example version check
            'extended_liquid': (self.build >= 20173)
        }
        return feature_requirements.get(feature, True)

class ADTFile:
    """Core ADT file handler with memory mapping"""
    def __init__(self, path: Path):
        self.path = path
        self.file: Optional[BinaryIO] = None
        self.mm: Optional[mmap.mmap] = None
        self.version = ADTVersion()
        self.chunk_index: Dict[str, List[ADTChunkRef]] = defaultdict(list)
        self.coordinate_info: Optional[Tuple[int, int]] = None
        
        # Initialize
        self._open_and_index()

    def _open_and_index(self) -> None:
        """Open file and build chunk index"""
        try:
            self.file = open(self.path, 'rb')
            self.mm = mmap.mmap(self.file.fileno(), 0, access=mmap.ACCESS_READ)
            self._parse_coordinates()
            self._build_chunk_index()
            self._read_version()
        except Exception as e:
            logger.error(f"Failed to open ADT file {self.path}: {e}")
            self.close()
            raise

    def _parse_coordinates(self) -> None:
        """Extract map coordinates from filename"""
        try:
            parts = self.path.stem.split('_')
            if len(parts) >= 3:
                self.coordinate_info = (int(parts[-2]), int(parts[-1]))
        except ValueError:
            logger.warning(f"Could not parse coordinates from filename: {self.path.name}")

    def _build_chunk_index(self) -> None:
        """Index all chunks in the file"""
        pos = 0
        while pos < len(self.mm):
            if pos + 8 > len(self.mm):
                break
                
            try:
                magic = self.mm[pos:pos+4].decode('ascii')
                size = struct.unpack('<I', self.mm[pos+4:pos+8])[0]
                
                chunk_ref = ADTChunkRef(
                    offset=pos + 8,  # Start of chunk data
                    size=size,
                    magic=magic,
                    header_offset=pos
                )
                
                self.chunk_index[magic].append(chunk_ref)
                pos += 8 + size
                
            except Exception as e:
                logger.error(f"Error indexing chunk at offset {pos}: {e}")
                break

    def _read_version(self) -> None:
        """Read version information if available"""
        version_chunks = self.chunk_index.get('MVER', [])
        if version_chunks:
            version_data = self.read_chunk_data(version_chunks[0])
            self.version.parse(version_data)

    def read_chunk_data(self, chunk_ref: ADTChunkRef) -> bytes:
        """Read raw chunk data"""
        return self.mm[chunk_ref.offset:chunk_ref.offset + chunk_ref.size]

    def get_chunks_by_type(self, chunk_type: str) -> Iterator[Tuple[ADTChunkRef, bytes]]:
        """Get all chunks of a specific type with their data"""
        for chunk_ref in self.chunk_index.get(chunk_type, []):
            yield chunk_ref, self.read_chunk_data(chunk_ref)

    def get_mcnk(self, x: int, y: int) -> Optional[Tuple[ADTChunkRef, bytes]]:
        """Get specific MCNK chunk by coordinates"""
        if not 0 <= x < 16 or not 0 <= y < 16:
            raise ValueError("Coordinates must be 0-15")
            
        chunk_idx = y * 16 + x
        mcnk_chunks = self.chunk_index.get('MCNK', [])
        
        if chunk_idx < len(mcnk_chunks):
            chunk_ref = mcnk_chunks[chunk_idx]
            return chunk_ref, self.read_chunk_data(chunk_ref)
        return None

    def dump_chunk_info(self) -> None:
        """Debug: Dump information about all chunks"""
        for magic, chunks in self.chunk_index.items():
            print(f"\n{magic} chunks ({len(chunks)}):")
            for idx, chunk in enumerate(chunks):
                print(f"  {idx}: offset={chunk.offset}, size={chunk.size}")

    def close(self) -> None:
        """Close file handles"""
        if self.mm:
            self.mm.close()
        if self.file:
            self.file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
