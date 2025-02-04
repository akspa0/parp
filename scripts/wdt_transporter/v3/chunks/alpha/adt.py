"""ADT file handling for Alpha WoW files."""
from dataclasses import dataclass
from pathlib import Path
import struct
from typing import BinaryIO, List, Optional, Tuple

from ..base import Chunk
from .mcnk import McnkChunk


@dataclass
class McInEntry:
    """MCIN entry structure (16 bytes)."""
    offset: int = 0
    size: int = 0
    flags: int = 0
    async_id: int = 0

    @classmethod
    def from_bytes(cls, data: bytes) -> 'McInEntry':
        """Create entry from 16 bytes."""
        offset, size, flags, async_id = struct.unpack('<4I', data)
        return cls(offset, size, flags, async_id)

    def to_bytes(self) -> bytes:
        """Convert entry to 16 bytes."""
        return struct.pack('<4I', self.offset, self.size, self.flags, self.async_id)


@dataclass
class AlphaAdt:
    """Alpha ADT file format handler.
    
    This follows the structure from gp/wowfiles/alpha/AdtAlpha.h
    but simplified for Python. Key differences:
    - Uses raw chunk names (e.g. 'RDHM' not 'MHDR')
    - Stores raw chunk data until needed
    """
    mhdr: Chunk  # RDHM (MHDR) chunk
    mcin: Chunk  # NICM (MCIN) chunk
    mtex: Chunk  # XETM (MTEX) chunk
    mddf: Chunk  # FDDM (MDDF) chunk
    modf: Chunk  # FDOM (MODF) chunk
    mcnk: List[Chunk]  # KNCM (MCNK) chunks (256 total)
    adt_num: int  # ADT number in 64x64 grid

    @classmethod
    def read_from_wdt(cls, wdt_path: Path, offset: int, adt_num: int) -> 'AlphaAdt':
        """Read ADT data from WDT file at given offset."""
        chunks = {}
        mcnk_chunks = []

        with open(wdt_path, 'rb') as f:
            # Seek to ADT data
            f.seek(offset)

            # Read MHDR
            mhdr = Chunk.read(f)
            if not mhdr or mhdr.letters != 'RDHM':
                raise ValueError(f"Expected RDHM chunk at {offset}, got {mhdr.letters if mhdr else 'EOF'}")
            chunks['RDHM'] = mhdr

            # Get chunk offsets from MHDR
            mhdr_start = offset + 8  # Skip chunk header
            mcin_offset = struct.unpack('<I', mhdr.data[0:4])[0]
            mtex_offset = struct.unpack('<I', mhdr.data[4:8])[0]
            mddf_offset = struct.unpack('<I', mhdr.data[12:16])[0]
            modf_offset = struct.unpack('<I', mhdr.data[20:24])[0]

            # Read MCIN
            f.seek(mhdr_start + mcin_offset)
            mcin = Chunk.read(f)
            if not mcin or mcin.letters != 'NICM':
                raise ValueError(f"Expected NICM chunk at {mhdr_start + mcin_offset}")
            chunks['NICM'] = mcin

            # Read MTEX
            f.seek(mhdr_start + mtex_offset)
            mtex = Chunk.read(f)
            if not mtex or mtex.letters != 'XETM':
                raise ValueError(f"Expected XETM chunk at {mhdr_start + mtex_offset}")
            chunks['XETM'] = mtex

            # Read MDDF
            f.seek(mhdr_start + mddf_offset)
            mddf = Chunk.read(f)
            if not mddf or mddf.letters != 'FDDM':
                raise ValueError(f"Expected FDDM chunk at {mhdr_start + mddf_offset}")
            chunks['FDDM'] = mddf

            # Read MODF
            f.seek(mhdr_start + modf_offset)
            modf = Chunk.read(f)
            if not modf or modf.letters != 'FDOM':
                raise ValueError(f"Expected FDOM chunk at {mhdr_start + modf_offset}")
            chunks['FDOM'] = modf

            # Read MCNK chunks
            # Create empty list to store chunks in x/z order
            mcnk_by_coords = [[None for _ in range(16)] for _ in range(16)]

            # Read chunks in file order
            for i in range(256):
                mcnk_offset = struct.unpack('<I', mcin.data[i*16:i*16+4])[0]
                f.seek(mcnk_offset)
                mcnk = Chunk.read(f)
                if not mcnk or mcnk.letters != 'KNCM':
                    raise ValueError(f"Expected KNCM chunk at {mcnk_offset}")
                # Convert to WotLK format
                mcnk_obj = McnkChunk.from_chunk(mcnk)
                # Store in x/z grid
                mcnk_by_coords[mcnk_obj.ix][mcnk_obj.iy] = mcnk_obj.to_wotlk()

            # Convert grid to linear list in correct order (x * 16 + z)
            for i in range(256):
                x = i // 16  # Integer division
                z = i % 16   # Remainder
                chunk = mcnk_by_coords[x][z]
                if not chunk:
                    raise ValueError(f"Missing MCNK chunk at {x},{z}")
                mcnk_chunks.append(chunk)

        return cls(
            mhdr=chunks['RDHM'],
            mcin=chunks['NICM'],
            mtex=chunks['XETM'],
            mddf=chunks['FDDM'],
            modf=chunks['FDOM'],
            mcnk=mcnk_chunks,
            adt_num=adt_num
        )

    def write_to_file(self, path: Path) -> None:
        """Write ADT to file in WotLK format.
        
        Following noggit-red's MapTile.cpp saveTile() implementation:
        1. Write MVER chunk with version 18
        2. Write chunks in exact order:
           MHDR, MCIN, MTEX, MDDF, MODF, MCNK[256]
        """
        # Calculate chunk offsets
        current_pos = 0

        # MVER (12 bytes)
        mver_pos = current_pos
        current_pos += 12  # 4 (magic) + 4 (size) + 4 (version)

        # MHDR (136 bytes)
        mhdr_pos = current_pos
        current_pos += 8 + len(self.mhdr.data)  # 4 (magic) + 4 (size) + data

        # MCIN (4104 bytes)
        mcin_pos = current_pos
        current_pos += 8 + len(self.mcin.data)  # 4 (magic) + 4 (size) + data

        # MTEX
        mtex_pos = current_pos
        current_pos += 8 + len(self.mtex.data)  # 4 (magic) + 4 (size) + data

        # MDDF (optional)
        mddf_pos = current_pos if self.mddf.size > 0 else 0
        if mddf_pos:
            current_pos += 8 + len(self.mddf.data)  # 4 (magic) + 4 (size) + data

        # MODF (optional)
        modf_pos = current_pos if self.modf.size > 0 else 0
        if modf_pos:
            current_pos += 8 + len(self.modf.data)  # 4 (magic) + 4 (size) + data

        # MCNK offsets
        mcnk_offsets = []
        for mcnk in self.mcnk:
            mcnk_offsets.append(current_pos)
            current_pos += 8 + mcnk.size  # 4 (magic) + 4 (size) + data

        # Update MHDR offsets
        mhdr_data = bytearray(self.mhdr.data)
        struct.pack_into('<I', mhdr_data, 0, mcin_pos - 0x14)  # mcin offset
        struct.pack_into('<I', mhdr_data, 4, mtex_pos - 0x14)  # mtex offset
        if mddf_pos:
            struct.pack_into('<I', mhdr_data, 12, mddf_pos - 0x14)  # mddf offset
        if modf_pos:
            struct.pack_into('<I', mhdr_data, 20, modf_pos - 0x14)  # modf offset

        # Update MCIN entries while preserving size/flags/asyncID
        mcin_data = bytearray()
        for i in range(256):
            entry = McInEntry.from_bytes(self.mcin.data[i*16:(i+1)*16])
            entry.offset = mcnk_offsets[i]  # Update offset only
            mcin_data.extend(entry.to_bytes())

        # Write file
        with open(path, 'wb') as f:
            # Write MVER chunk
            f.write(b'REVM')  # Magic (reversed)
            f.write(struct.pack('<I', 4))  # Size
            f.write(struct.pack('<I', 18))  # Version

            # Write MHDR chunk
            f.write(b'RDHM')
            f.write(struct.pack('<I', len(mhdr_data)))
            f.write(mhdr_data)

            # Write MCIN chunk
            f.write(b'NICM')
            f.write(struct.pack('<I', len(mcin_data)))
            f.write(mcin_data)

            # Write MTEX chunk
            f.write(b'XETM')
            f.write(struct.pack('<I', len(self.mtex.data)))
            f.write(self.mtex.data)

            # Write MDDF chunk (optional)
            if self.mddf.size > 0:
                f.write(b'FDDM')
                f.write(struct.pack('<I', len(self.mddf.data)))
                f.write(self.mddf.data)

            # Write MODF chunk (optional)
            if self.modf.size > 0:
                f.write(b'FDOM')
                f.write(struct.pack('<I', len(self.modf.data)))
                f.write(self.modf.data)

            # Write MCNK chunks
            for mcnk in self.mcnk:
                f.write(b'KNCM')
                f.write(struct.pack('<I', mcnk.size))
                f.write(mcnk.data)

    def get_name(self, wdt_name: str) -> str:
        """Get ADT filename from WDT name and coordinates."""
        x = self.get_x_coord()
        y = self.get_y_coord()
        base = wdt_name.rsplit('.', 1)[0]  # Remove .wdt extension
        return f"{base}_{x:02d}_{y:02d}.adt"

    def get_x_coord(self) -> int:
        """Get X coordinate in 64x64 grid."""
        return self.adt_num % 64

    def get_y_coord(self) -> int:
        """Get Y coordinate in 64x64 grid."""
        return self.adt_num // 64

    def __str__(self) -> str:
        return f"ADT {self.get_x_coord()}_{self.get_y_coord()} " \
               f"({len(self.mcnk)} MCNK chunks)"
