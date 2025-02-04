"""ADT file handling for WotLK WoW files."""
from dataclasses import dataclass
from pathlib import Path
import struct
from typing import BinaryIO, List, Optional, Tuple

from ..base import Chunk


@dataclass
class WotlkAdt:
    """WotLK ADT file format handler.
    
    This follows the structure from noggit-red MapTile.h and MapHeaders.h.
    Key differences:
    - Uses raw chunk names (e.g. 'REVM' not 'MVER')
    - Stores raw chunk data until needed
    """
    mver: Chunk  # REVM (MVER) chunk
    mhdr: Chunk  # RDHM (MHDR) chunk
    mcin: Chunk  # NICM (MCIN) chunk
    mtex: Chunk  # XETM (MTEX) chunk
    mmdx: Chunk  # XDMM (MMDX) chunk
    mmid: Chunk  # DIMM (MMID) chunk
    mwmo: Chunk  # OMWM (MWMO) chunk
    mwid: Chunk  # DIWM (MWID) chunk
    mddf: Chunk  # FDDM (MDDF) chunk
    modf: Chunk  # FDOM (MODF) chunk
    mcnk: List[Chunk]  # KNCM (MCNK) chunks (256 total)
    mfbo: Optional[Chunk] = None  # OBFM (MFBO) chunk (optional)
    mtxf: Optional[Chunk] = None  # FXTM (MTXF) chunk (optional)

    @classmethod
    def from_alpha_adt(cls, alpha_adt: 'AlphaAdt', model_names: List[str], object_names: List[str]) -> 'WotlkAdt':
        """Convert Alpha ADT to WotLK format."""
        # Create MVER chunk (version 18)
        mver_data = struct.pack('<I', 18)
        mver = Chunk(letters='REVM', size=4, data=mver_data)

        # Create MMDX chunk from model names
        mmdx_data = b'\0'.join(name.encode('ascii') for name in model_names) + b'\0' if model_names else b''
        mmdx = Chunk(letters='XDMM', size=len(mmdx_data), data=mmdx_data)

        # Create MMID chunk (model indices)
        mmid_data = struct.pack('<I', 0)
        mmid = Chunk(letters='DIMM', size=4, data=mmid_data)

        # Create MWMO chunk from object names
        mwmo_data = b'\0'.join(name.encode('ascii') for name in object_names) + b'\0' if object_names else b''
        mwmo = Chunk(letters='OMWM', size=len(mwmo_data), data=mwmo_data)

        # Create MWID chunk (object indices)
        mwid_data = struct.pack('<I', 0)
        mwid = Chunk(letters='DIWM', size=4, data=mwid_data)

        # Calculate chunk offsets
        # Start after MVER (8 + 4) and MHDR (8 + 64)
        offset = 84  # 8 (MVER header) + 4 (version) + 8 (MHDR header) + 64 (MHDR data)

        mcin_offset = offset
        offset += 8 + 16 * 256  # header + (16 bytes per MCNK entry * 256 entries)

        mtex_offset = offset
        offset += 8 + alpha_adt.mtex.size

        mmdx_offset = offset
        offset += 8 + len(mmdx_data)

        mmid_offset = offset
        offset += 8 + 4  # header + one index

        mwmo_offset = offset
        offset += 8 + len(mwmo_data)

        mwid_offset = offset
        offset += 8 + 4  # header + one index

        mddf_offset = offset
        offset += 8 + alpha_adt.mddf.size

        modf_offset = offset
        offset += 8 + alpha_adt.modf.size

        # Create MHDR chunk with proper offsets
        mhdr_data = bytearray(64)  # 64 bytes total
        mhdr_data[0:4] = struct.pack('<I', 0)  # flags = 0
        mhdr_data[4:8] = struct.pack('<I', mcin_offset)  # Offsets are absolute from start of MHDR data
        mhdr_data[8:12] = struct.pack('<I', mtex_offset)
        mhdr_data[12:16] = struct.pack('<I', mmdx_offset)
        mhdr_data[16:20] = struct.pack('<I', mmid_offset)
        mhdr_data[20:24] = struct.pack('<I', mwmo_offset)
        mhdr_data[24:28] = struct.pack('<I', mwid_offset)
        mhdr_data[28:32] = struct.pack('<I', mddf_offset)
        mhdr_data[32:36] = struct.pack('<I', modf_offset)
        # mfbo_offset = 0 (not used)
        # mh2o_offset = 0 (not used)
        # mtxf_offset = 0 (not used)
        mhdr = Chunk(letters='RDHM', size=64, data=bytes(mhdr_data))

        # Start MCNK offset calculation after all other chunks
        mcnk_start = offset  # Don't add chunk header size - it's included in the offset

        # Create MCIN chunk with updated offsets
        mcin_data = bytearray(16 * 256)  # 16 bytes per entry, 256 entries
        mcnk_offset = mcnk_start
        for i in range(256):
            # Get original entry
            entry_offset = i * 16
            entry = alpha_adt.mcin.data[entry_offset:entry_offset + 16]
            size = struct.unpack('<I', entry[4:8])[0]  # Get size from original entry
            flags = struct.unpack('<I', entry[8:12])[0]  # Get flags from original entry
            layer = struct.unpack('<I', entry[12:16])[0]  # Get layer from original entry
            
            # Write updated entry
            mcin_data[entry_offset:entry_offset + 4] = struct.pack('<I', mcnk_offset)  # New offset
            mcin_data[entry_offset + 4:entry_offset + 8] = struct.pack('<I', size + 40)  # Add subchunk headers only
            mcin_data[entry_offset + 8:entry_offset + 12] = struct.pack('<I', flags)  # Keep original flags
            mcin_data[entry_offset + 12:entry_offset + 16] = struct.pack('<I', layer)  # Keep original layer
            
            mcnk_offset += size + 40  # Add chunk size + subchunk headers (40)

        mcin = Chunk(letters='NICM', size=16 * 256, data=bytes(mcin_data))

        # Copy remaining chunks
        mtex = alpha_adt.mtex
        mddf = alpha_adt.mddf
        modf = alpha_adt.modf
        mcnk = alpha_adt.mcnk

        return cls(
            mver=mver,
            mhdr=mhdr,
            mcin=mcin,
            mtex=mtex,
            mmdx=mmdx,
            mmid=mmid,
            mwmo=mwmo,
            mwid=mwid,
            mddf=mddf,
            modf=modf,
            mcnk=mcnk
        )

    def write(self, path: Path) -> None:
        """Write ADT to file in WotLK format.
        
        Chunks must be written in the correct order as specified in
        noggit-red MapTile.h:
        
        MVER, MHDR, MCIN, MTEX, MMDX, MMID, MWMO, MWID,
        MDDF, MODF, MCNK[256], MFBO?, MTXF?
        """
        with open(path, 'wb') as f:
            self.mver.write(f)
            self.mhdr.write(f)
            self.mcin.write(f)
            self.mtex.write(f)
            self.mmdx.write(f)
            self.mmid.write(f)
            self.mwmo.write(f)
            self.mwid.write(f)
            self.mddf.write(f)
            self.modf.write(f)
            for mcnk in self.mcnk:
                mcnk.write(f)
            if self.mfbo:
                self.mfbo.write(f)
            if self.mtxf:
                self.mtxf.write(f)