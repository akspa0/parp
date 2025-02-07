"""ADT file handling for Alpha WoW files."""
from dataclasses import dataclass
from pathlib import Path
import struct
from typing import Dict, List, Optional, Tuple

from ..base import Chunk
from .mcnk import McnkChunk


@dataclass
class AlphaAdt:
    """ADT file format handler.
    
    This follows the structure from gp/wowfiles/alpha/AdtAlpha.h.
    Key differences:
    - Uses raw chunk names (e.g. 'REVM' not 'MVER')
    - Stores raw chunk data until needed
    """
    mhdr: Chunk  # RDHM (MHDR) chunk
    mcin: Chunk  # NICM (MCIN) chunk
    mtex: Chunk  # XETM (MTEX) chunk
    mddf: Chunk  # FDDM (MDDF) chunk
    modf: Chunk  # FDOM (MODF) chunk
    mcnk: List[Chunk]  # KNCM (MCNK) chunks (256 total)
    adt_x: int = 0  # ADT X coordinate (0-63)
    adt_y: int = 0  # ADT Y coordinate (0-63)

    @classmethod
    def read_from_wdt(cls, wdt_path: Path, offset: int, adt_num: int) -> 'AlphaAdt':
        """Read ADT from WDT file at given offset."""
        # Calculate ADT coordinates
        adt_x = adt_num % 64
        adt_y = adt_num // 64

        chunks = {}
        mcnk_chunks = []

        with open(wdt_path, 'rb') as f:
            f.seek(offset)

            # First read non-MCNK chunks
            while True:
                chunk = Chunk.read(f)
                if not chunk:
                    break

                if chunk.letters != 'KNCM':
                    chunks[chunk.letters] = chunk
                    if len(chunks) >= 5:  # We have all non-MCNK chunks
                        break

            # Validate required chunks
            if 'RDHM' not in chunks:
                raise ValueError("Missing MHDR chunk")
            if 'NICM' not in chunks:
                raise ValueError("Missing MCIN chunk")
            if 'XETM' not in chunks:
                raise ValueError("Missing MTEX chunk")
            if 'FDDM' not in chunks:
                raise ValueError("Missing MDDF chunk")
            if 'FDOM' not in chunks:
                raise ValueError("Missing MODF chunk")

            # Get MCNK offsets from MCIN chunk
            mcnk_offsets = []
            mcin_data = chunks['NICM'].data
            for i in range(256):
                offset_start = i * 16  # Each MCIN entry is 16 bytes
                mcnk_offset = struct.unpack('<I', mcin_data[offset_start:offset_start + 4])[0]
                if mcnk_offset > 0:
                    mcnk_offsets.append(mcnk_offset)

            # Read MCNK chunks using offsets
            for mcnk_offset in mcnk_offsets:
                f.seek(mcnk_offset)
                chunk = Chunk.read(f)
                if not chunk or chunk.letters != 'KNCM':
                    raise ValueError(f"Invalid MCNK chunk at offset {mcnk_offset}")
                mcnk_chunks.append(chunk)

            if len(mcnk_chunks) != 256:
                raise ValueError(f"Expected 256 MCNK chunks, got {len(mcnk_chunks)}")

        return cls(
            mhdr=chunks['RDHM'],
            mcin=chunks['NICM'],
            mtex=chunks['XETM'],
            mddf=chunks['FDDM'],
            modf=chunks['FDOM'],
            mcnk=mcnk_chunks,
            adt_x=adt_x,
            adt_y=adt_y
        )

    def get_name(self, wdt_name: str) -> str:
        """Get ADT filename from WDT name and coordinates."""
        # Remove .wdt extension
        base_name = wdt_name[:-4] if wdt_name.endswith('.wdt') else wdt_name
        return f"{base_name}_{self.adt_x}_{self.adt_y}.adt"

    def to_wotlk(self) -> List[Chunk]:
        """Convert to WotLK format.
        
        Following gp/wowfiles/alpha/AdtAlpha.cpp toAdtLk() implementation:
        - Copy basic chunks (MHDR, MCIN, MTEX, MDDF, MODF)
        - Convert MCNK chunks to WotLK format
        """
        chunks = []

        # Create MVER chunk (version 18)
        mver_data = struct.pack('<I', 18)
        chunks.append(Chunk(letters='REVM', size=4, data=mver_data))

        # Copy basic chunks
        chunks.append(self.mhdr)
        chunks.append(self.mcin)
        chunks.append(self.mtex)
        chunks.append(self.mddf)
        chunks.append(self.modf)

        # Convert MCNK chunks
        for i, chunk in enumerate(self.mcnk):
            # Calculate MCNK coordinates within ADT
            mcnk_x = i % 16
            mcnk_y = i // 16
            mcnk = McnkChunk.from_chunk(chunk, self.adt_x, self.adt_y)
            chunks.append(mcnk.to_wotlk())

        return chunks

    def write(self, path: Path) -> None:
        """Write ADT to file in WotLK format."""
        chunks = self.to_wotlk()
        with open(path, 'wb') as f:
            for chunk in chunks:
                chunk.write(f)
