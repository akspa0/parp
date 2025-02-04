"""ADT file handling for Alpha WoW files."""
from dataclasses import dataclass
from pathlib import Path
import struct
from typing import BinaryIO, List, Optional, Tuple

from ..base import Chunk
from .mcnk import McnkChunk


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
            for i in range(256):
                mcnk_offset = struct.unpack('<I', mcin.data[i*16:i*16+4])[0]
                f.seek(mcnk_offset)
                mcnk = Chunk.read(f)
                if not mcnk or mcnk.letters != 'KNCM':
                    raise ValueError(f"Expected KNCM chunk at {mcnk_offset}")
                # Convert to WotLK format
                mcnk_obj = McnkChunk.from_chunk(mcnk)
                mcnk_chunks.append(mcnk_obj.to_wotlk())

        return cls(
            mhdr=chunks['RDHM'],
            mcin=chunks['NICM'],
            mtex=chunks['XETM'],
            mddf=chunks['FDDM'],
            modf=chunks['FDOM'],
            mcnk=mcnk_chunks,
            adt_num=adt_num
        )

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
