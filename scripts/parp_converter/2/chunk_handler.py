from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, BinaryIO
import struct
import mmap
import logging
from enum import IntFlag
from pathlib import Path

class ChunkError(Exception):
    """Base exception for chunk processing errors"""
    pass

class MCNKFlags(IntFlag):
    """MCNK chunk flags"""
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
    """Chunk header information"""
    magic: str
    size: int
    offset: int  # Offset to chunk data start (after header)

@dataclass
class ChunkRef:
    """Reference to a chunk within the file"""
    offset: int  # Offset to chunk data
    size: int    # Size of chunk data
    magic: str   # Chunk magic string
    header_offset: int  # Offset to chunk header

    @property
    def data_range(self) -> Tuple[int, int]:
        """Return range of chunk data (start, end)"""
        return (self.offset, self.offset + self.size)

@dataclass
class MCNKHeader:
    """Base MCNK header structure"""
    flags: int
    index_x: int
    index_y: int
    n_layers: int
    m2_number: int
    mcvt_offset: int  # height map
    mcnr_offset: int  # normals
    mcly_offset: int  # layers
    mcrf_offset: int  # refs
    mcal_offset: int  # alpha maps
    mcal_size: int
    mcsh_offset: int  # shadows
    mcsh_size: int
    area_id: int
    wmo_number: int
    holes: int
    ground_effects: List[int]  # 4 maps
    pred_tex: int
    n_effect_doodad: int
    mcse_offset: int
    n_snd_emitters: int
    mclq_offset: int  # liquid
    mclq_size: int
    pos: Tuple[float, float, float]
    mccv_offset: int
    mclv_offset: int
    unused: int

@dataclass
class MCNKAlphaHeader:
    """Alpha format MCNK header structure"""
    flags: int
    index_x: int
    index_y: int
    unknown1: float
    n_layers: int
    m2_number: int
    mcvt_offset: int
    mcnr_offset: int
    mcly_offset: int
    mcrf_offset: int
    mcal_offset: int
    mcal_size: int
    mcsh_offset: int
    mcsh_size: int
    unknown3: int
    wmo_number: int
    holes: int
    ground_effects: List[int]  # 4 maps
    unknown6: int
    unknown7: int
    mcnk_chunks_size: int
    unknown8: int
    mclq_offset: int
    unused: List[int]  # 6 unused values

class MCNKInfo:
    """MCNK chunk information with sub-chunks"""
    def __init__(self, data: bytes, offset: int, is_alpha: bool = False):
        self.offset = offset
        self.is_alpha = is_alpha

        if is_alpha:
            self._parse_alpha_header(data)
        else:
            self._parse_retail_header(data)

        # Sub-chunk data (to be populated during parsing)
        self.mcvt_data: Optional[bytes] = None  # height map
        self.mcnr_data: Optional[bytes] = None  # normals
        self.mcly_data: Optional[bytes] = None  # layers
        self.mcrf_data: Optional[bytes] = None  # refs
        self.mcal_data: Optional[bytes] = None  # alpha maps
        self.mcsh_data: Optional[bytes] = None  # shadows
        self.mclq_data: Optional[bytes] = None  # liquid

    def _parse_alpha_header(self, data: bytes):
        """Parse Alpha format MCNK header"""
        self.header = MCNKAlphaHeader(
            flags=struct.unpack('<I', data[0:4])[0],
            index_x=struct.unpack('<I', data[4:8])[0],
            index_y=struct.unpack('<I', data[8:12])[0],
            unknown1=struct.unpack('<f', data[12:16])[0],
            n_layers=struct.unpack('<I', data[16:20])[0],
            m2_number=struct.unpack('<I', data[20:24])[0],
            mcvt_offset=struct.unpack('<I', data[24:28])[0],
            mcnr_offset=struct.unpack('<I', data[28:32])[0],
            mcly_offset=struct.unpack('<I', data[32:36])[0],
            mcrf_offset=struct.unpack('<I', data[36:40])[0],
            mcal_offset=struct.unpack('<I', data[40:44])[0],
            mcal_size=struct.unpack('<I', data[44:48])[0],
            mcsh_offset=struct.unpack('<I', data[48:52])[0],
            mcsh_size=struct.unpack('<I', data[52:56])[0],
            unknown3=struct.unpack('<I', data[56:60])[0],
            wmo_number=struct.unpack('<I', data[60:64])[0],
            holes=struct.unpack('<I', data[64:68])[0],
            ground_effects=[struct.unpack('<I', data[68+i*4:72+i*4])[0] for i in range(4)],
            unknown6=struct.unpack('<I', data[84:88])[0],
            unknown7=struct.unpack('<I', data[88:92])[0],
            mcnk_chunks_size=struct.unpack('<I', data[92:96])[0],
            unknown8=struct.unpack('<I', data[96:100])[0],
            mclq_offset=struct.unpack('<I', data[100:104])[0],
            unused=[struct.unpack('<I', data[104+i*4:108+i*4])[0] for i in range(6)]
        )

        # Set common properties
        self.flags = MCNKFlags(self.header.flags)
        self.idx_x = self.header.index_x
        self.idx_y = self.header.index_y
        self.n_layers = self.header.n_layers
        self.n_doodad_refs = self.header.m2_number

        # Set offsets
        self.mcvt_offset = self.header.mcvt_offset
        self.mcnr_offset = self.header.mcnr_offset
        self.mcly_offset = self.header.mcly_offset
        self.mcrf_offset = self.header.mcrf_offset
        self.mcal_offset = self.header.mcal_offset
        self.mcsh_offset = self.header.mcsh_offset
        self.mclq_offset = self.header.mclq_offset

    def _parse_retail_header(self, data: bytes):
        """Parse retail format MCNK header"""
        self.header = MCNKHeader(
            flags=struct.unpack('<I', data[0:4])[0],
            index_x=struct.unpack('<I', data[4:8])[0],
            index_y=struct.unpack('<I', data[8:12])[0],
            n_layers=struct.unpack('<I', data[12:16])[0],
            m2_number=struct.unpack('<I', data[16:20])[0],
            mcvt_offset=struct.unpack('<I', data[20:24])[0],
            mcnr_offset=struct.unpack('<I', data[24:28])[0],
            mcly_offset=struct.unpack('<I', data[28:32])[0],
            mcrf_offset=struct.unpack('<I', data[32:36])[0],
            mcal_offset=struct.unpack('<I', data[36:40])[0],
            mcal_size=struct.unpack('<I', data[40:44])[0],
            mcsh_offset=struct.unpack('<I', data[44:48])[0],
            mcsh_size=struct.unpack('<I', data[48:52])[0],
            area_id=struct.unpack('<I', data[52:56])[0],
            wmo_number=struct.unpack('<I', data[56:60])[0],
            holes=struct.unpack('<I', data[60:64])[0],
            ground_effects=[struct.unpack('<I', data[64+i*4:68+i*4])[0] for i in range(4)],
            pred_tex=struct.unpack('<I', data[80:84])[0],
            n_effect_doodad=struct.unpack('<I', data[84:88])[0],
            mcse_offset=struct.unpack('<I', data[88:92])[0],
            n_snd_emitters=struct.unpack('<I', data[92:96])[0],
            mclq_offset=struct.unpack('<I', data[96:100])[0],
            mclq_size=struct.unpack('<I', data[100:104])[0],
            pos=(
                struct.unpack('<f', data[104:108])[0],
                struct.unpack('<f', data[108:112])[0],
                struct.unpack('<f', data[112:116])[0]
            ),
            mccv_offset=struct.unpack('<I', data[116:120])[0],
            mclv_offset=struct.unpack('<I', data[120:124])[0],
            unused=struct.unpack('<I', data[124:128])[0]
        )

        # Set common properties
        self.flags = MCNKFlags(self.header.flags)
        self.idx_x = self.header.index_x
        self.idx_y = self.header.index_y
        self.n_layers = self.header.n_layers
        self.n_doodad_refs = self.header.m2_number

        # Set offsets
        self.mcvt_offset = self.header.mcvt_offset
        self.mcnr_offset = self.header.mcnr_offset
        self.mcly_offset = self.header.mcly_offset
        self.mcrf_offset = self.header.mcrf_offset
        self.mcal_offset = self.header.mcal_offset
        self.mcsh_offset = self.header.mcsh_offset
        self.mclq_offset = self.header.mclq_offset

        # Sub-chunk data (to be populated during parsing)
        self.mcvt_data: Optional[bytes] = None
        self.mcnr_data: Optional[bytes] = None
        self.mcly_data: Optional[bytes] = None
        self.mcrf_data: Optional[bytes] = None
        self.mcal_data: Optional[bytes] = None
        self.mcsh_data: Optional[bytes] = None
        self.mclq_data: Optional[bytes] = None

    def has_subchunk(self, subchunk: str) -> bool:
        """Check if MCNK has a specific sub-chunk"""
        offset_map = {
            'MCVT': self.mcvt_offset,
            'MCNR': self.mcnr_offset,
            'MCLY': self.mcly_offset,
            'MCRF': self.mcrf_offset,
            'MCAL': self.mcal_offset,
            'MCSH': self.mcsh_offset,
            'MCLQ': self.mclq_offset
        }
        return offset_map.get(subchunk, 0) > 0

class WDTFile:
    """Memory-mapped WDT file handler"""
    def __init__(self, path: Path):
        self.path = path
        self.file: Optional[BinaryIO] = None
        self.mm: Optional[mmap.mmap] = None
        self.chunk_index: Dict[str, List[ChunkRef]] = {}
        self.reverse_names = False

    def open(self):
        """Open and memory-map the file"""
        try:
            self.file = open(self.path, 'rb')
            self.mm = mmap.mmap(self.file.fileno(), 0, access=mmap.ACCESS_READ)
            self._detect_name_reversal()
            self._build_chunk_index()
        except Exception as e:
            logging.error(f"Failed to open WDT file {self.path}: {e}")
            self.close()
            raise

    def _detect_name_reversal(self):
        """Detect if chunk names need to be reversed"""
        pos = 0
        while pos + 8 <= len(self.mm):
            magic = self.mm[pos:pos+4]
            if magic in [b'MVER', b'MPHD', b'MAIN']:
                self.reverse_names = False
                return
            if magic[::-1] in [b'MVER', b'MPHD', b'MAIN']:
                self.reverse_names = True
                return
            size = struct.unpack('<I', self.mm[pos+4:pos+8])[0]
            pos += 8 + size

        logging.warning("Could not definitively detect chunk name orientation")
        self.reverse_names = False

    def _build_chunk_index(self):
        """Index all chunks in the file"""
        pos = 0
        while pos < len(self.mm):
            if pos + 8 > len(self.mm):
                break

            try:
                magic_raw = self.mm[pos:pos+4]
                magic = magic_raw[::-1] if self.reverse_names else magic_raw
                magic_str = magic.decode('ascii')
                size = struct.unpack('<I', self.mm[pos+4:pos+8])[0]

                chunk_ref = ChunkRef(
                    offset=pos + 8,  # Start of chunk data
                    size=size,
                    magic=magic_str,
                    header_offset=pos
                )

                if magic_str not in self.chunk_index:
                    self.chunk_index[magic_str] = []
                self.chunk_index[magic_str].append(chunk_ref)
                pos += 8 + size

            except Exception as e:
                logging.error(f"Error indexing chunk at offset {pos}: {e}")
                break

    def read_chunk_data(self, chunk_ref: ChunkRef) -> bytes:
        """Read raw chunk data"""
        return self.mm[chunk_ref.offset:chunk_ref.offset + chunk_ref.size]

    def get_chunks_by_type(self, chunk_type: str) -> List[Tuple[ChunkRef, bytes]]:
        """Get all chunks of a specific type with their data"""
        return [(ref, self.read_chunk_data(ref))
                for ref in self.chunk_index.get(chunk_type, [])]

    def parse_mcnk(self, chunk_ref: ChunkRef) -> MCNKInfo:
        """Parse MCNK chunk and its sub-chunks"""
        data = self.read_chunk_data(chunk_ref)
        mcnk = MCNKInfo(data, chunk_ref.offset)

        # Read sub-chunks
        if mcnk.mcvt_offset:
            mcnk.mcvt_data = data[mcnk.mcvt_offset:mcnk.mcnr_offset or len(data)]
        if mcnk.mcnr_offset:
            mcnk.mcnr_data = data[mcnk.mcnr_offset:mcnk.mcly_offset or len(data)]
        if mcnk.mcly_offset:
            mcnk.mcly_data = data[mcnk.mcly_offset:mcnk.mcrf_offset or len(data)]
        if mcnk.mcrf_offset:
            mcnk.mcrf_data = data[mcnk.mcrf_offset:mcnk.mcal_offset or len(data)]
        if mcnk.mcal_offset:
            mcnk.mcal_data = data[mcnk.mcal_offset:mcnk.mcsh_offset or len(data)]
        if mcnk.mcsh_offset:
            mcnk.mcsh_data = data[mcnk.mcsh_offset:len(data)]
        if mcnk.mclq_offset:
            mcnk.mclq_data = data[mcnk.mclq_offset:len(data)]

        return mcnk

    def get_record(self):
        """Retrieve the record from the WDT file"""
        # Implement the logic to retrieve the record
        # This is a placeholder implementation
        return "Record Data"

    def parse(self):
        """Parse the WDT file and handle each chunk"""
        with self:
            for chunk_type, chunks in self.chunk_index.items():
                if chunk_type == "MCNK":
                    for chunk_ref in chunks:
                        mcnk_info = self.parse_mcnk(chunk_ref)
                        # Process MCNKInfo as needed
                        pass

    def close(self):
        """Close file handles"""
        if self.mm:
            self.mm.close()
        if self.file:
            self.file.close()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()