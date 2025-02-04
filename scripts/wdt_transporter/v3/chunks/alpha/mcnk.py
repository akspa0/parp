"""MCNK chunk handling for Alpha WoW files."""
from dataclasses import dataclass
import struct
from typing import List, Optional, Tuple

from ..base import Chunk


@dataclass
class McnkChunk:
    """MCNK (terrain) chunk from Alpha WDT files.
    
    This follows the structure from gp/wowfiles/ChunkHeaders.h McnkAlphaHeader.
    Key differences:
    - Uses raw chunk names (e.g. 'KNCM' not 'MCNK')
    - Handles subchunks separately (MCVT, MCNR, etc.)
    """
    flags: int = 0
    ix: int = 0
    iy: int = 0
    unknown1: int = 0
    n_layers: int = 0
    n_doodad_refs: int = 0
    mcvt_offset: int = 0
    mcnr_offset: int = 0
    mcly_offset: int = 0
    mcrf_offset: int = 0
    mcal_offset: int = 0
    mcal_size: int = 0
    mcsh_offset: int = 0
    mcsh_size: int = 0
    area_id: int = 0
    n_mapobj_refs: int = 0
    holes: int = 0
    ground_effects: List[int] = None
    chunk_size: int = 0
    unknown8: int = 0
    mclq_offset: int = 0
    unused: List[int] = None
    header_data: bytes = b''  # Raw header data
    mcvt_data: bytes = b''    # Height data (580 bytes)
    mcnr_data: bytes = b''    # Normal data (448 bytes)
    mcly_data: bytes = b''    # Layer data
    mcrf_data: bytes = b''    # Model references
    mcsh_data: bytes = b''    # Shadow data
    mcal_data: bytes = b''    # Alpha data
    mclq_data: bytes = b''    # Liquid data

    @classmethod
    def from_chunk(cls, chunk: Chunk) -> 'McnkChunk':
        """Create MCNK chunk from raw chunk data."""
        if chunk.letters != 'KNCM':
            raise ValueError(f"Expected KNCM chunk, got {chunk.letters}")

        # Parse header (128 bytes)
        header = chunk.data[:128]
        (flags, ix, iy, unknown1, n_layers, n_doodad_refs,
         mcvt_offset, mcnr_offset, mcly_offset, mcrf_offset,
         mcal_offset, mcal_size, mcsh_offset, mcsh_size,
         area_id, n_mapobj_refs, holes,
         ground_effects1, ground_effects2, ground_effects3, ground_effects4,
         unknown6, unknown7, chunk_size, unknown8,
         mclq_offset, unused1, unused2, unused3, unused4, unused5, unused6) = struct.unpack('<32I', header)

        # Extract subchunk data
        data = chunk.data[128:]  # Skip header
        
        # Fixed size chunks
        mcvt_data = data[mcvt_offset:mcvt_offset + 580]  # MCVT is always 580 bytes
        mcnr_data = data[mcnr_offset:mcnr_offset + 448]  # MCNR is always 448 bytes
        
        # Variable size chunks - calculate sizes from offsets
        mcly_size = mcrf_offset - mcly_offset if mcrf_offset > mcly_offset else 0
        mcrf_size = mcal_offset - mcrf_offset if mcrf_offset > 0 and mcal_offset > mcrf_offset else 0
        
        mcly_data = data[mcly_offset:mcly_offset + mcly_size] if mcly_size > 0 else b''
        mcrf_data = data[mcrf_offset:mcrf_offset + mcrf_size] if mcrf_size > 0 else b''
        mcsh_data = data[mcsh_offset:mcsh_offset + mcsh_size] if mcsh_size > 0 else b''
        mcal_data = data[mcal_offset:mcal_offset + mcal_size] if mcal_size > 0 else b''
        mclq_data = data[mclq_offset:] if mclq_offset < len(data) else b''

        return cls(
            flags=flags,
            ix=ix,
            iy=iy,
            unknown1=unknown1,
            n_layers=n_layers,
            n_doodad_refs=n_doodad_refs,
            mcvt_offset=mcvt_offset,
            mcnr_offset=mcnr_offset,
            mcly_offset=mcly_offset,
            mcrf_offset=mcrf_offset,
            mcal_offset=mcal_offset,
            mcal_size=mcal_size,
            mcsh_offset=mcsh_offset,
            mcsh_size=mcsh_size,
            area_id=area_id,
            n_mapobj_refs=n_mapobj_refs,
            holes=holes,
            ground_effects=[ground_effects1, ground_effects2, ground_effects3, ground_effects4],
            chunk_size=chunk_size,
            unknown8=unknown8,
            mclq_offset=mclq_offset,
            unused=[unused1, unused2, unused3, unused4, unused5, unused6],
            header_data=header,
            mcvt_data=mcvt_data,
            mcnr_data=mcnr_data,
            mcly_data=mcly_data,
            mcrf_data=mcrf_data,
            mcsh_data=mcsh_data,
            mcal_data=mcal_data,
            mclq_data=mclq_data
        )

    def to_wotlk(self) -> Chunk:
        """Convert to WotLK format.
        
        Following gp/wowfiles/alpha/McnkAlpha.cpp toMcnkLk() implementation:
        - Copy basic fields from alpha header
        - Add new fields for WotLK format
        - Preserve subchunk data with proper offsets
        """
        # Start with header size
        offset = 136  # Header size (128) + padding (8)

        # Calculate subchunk offsets including chunk headers (8 bytes each)
        mcvt_offset = offset  # Offsets are absolute from start of chunk
        offset += 8 + 580  # chunk header (8) + data size (580)

        mcnr_offset = offset
        offset += 8 + 448  # chunk header (8) + data size (448)

        # MCLY (only if we have layers)
        has_mcly = bool(self.n_layers > 0 and self.mcly_data)
        mcly_offset = offset if has_mcly else 0
        if has_mcly:
            offset += 8 + len(self.mcly_data)

        # MCRF (only if we have doodads or WMOs)
        has_mcrf = bool((self.n_doodad_refs > 0 or self.n_mapobj_refs > 0) and self.mcrf_data)
        mcrf_offset = offset if has_mcrf else 0
        if has_mcrf:
            offset += 8 + len(self.mcrf_data)

        # MCSH comes before MCAL in retail
        has_mcsh = bool(self.flags & 0x1 and self.mcsh_data)  # Check has_mcsh flag
        mcsh_offset = offset if has_mcsh else 0
        mcsh_size = len(self.mcsh_data) if has_mcsh else 0
        if has_mcsh:
            offset += 8 + len(self.mcsh_data)

        # MCAL comes after MCSH
        has_mcal = bool(self.mcal_size > 0 and self.mcal_data)  # Check size in header
        mcal_offset = offset if has_mcal else 0
        mcal_size = len(self.mcal_data) + 8 if has_mcal else 0  # Include header size only if we have data
        if has_mcal:
            offset += 8 + len(self.mcal_data)

        # MCLQ (only if we have liquid flags)
        has_mclq = bool(self.flags & 0x0E and self.mclq_data)  # Check liquid flags (ocean/river/magma)
        mclq_offset = offset if has_mclq else 0
        mclq_size = len(self.mclq_data) + 8 if has_mclq else 0
        if has_mclq:
            offset += 8 + len(self.mclq_data)

        # Create new header (128 bytes)
        header = bytearray(128)

        # Copy basic fields
        header[0:4] = struct.pack('<I', self.flags)
        header[4:8] = struct.pack('<I', self.ix)
        header[8:12] = struct.pack('<I', self.iy)
        header[12:16] = struct.pack('<I', self.n_layers)
        header[16:20] = struct.pack('<I', self.n_doodad_refs)
        header[20:24] = struct.pack('<I', mcvt_offset)
        header[24:28] = struct.pack('<I', mcnr_offset)
        header[28:32] = struct.pack('<I', mcly_offset)
        header[32:36] = struct.pack('<I', mcrf_offset)
        header[36:40] = struct.pack('<I', mcal_offset)
        header[40:44] = struct.pack('<I', mcal_size)
        header[44:48] = struct.pack('<I', mcsh_offset)
        header[48:52] = struct.pack('<I', mcsh_size)
        header[52:56] = struct.pack('<I', self.area_id)
        header[56:60] = struct.pack('<I', self.n_mapobj_refs)
        header[60:64] = struct.pack('<I', self.holes)

        # Add new WotLK fields
        header[64:68] = struct.pack('<I', 0)  # predTex
        header[68:72] = struct.pack('<I', 0)  # nEffectDoodad
        header[72:76] = struct.pack('<I', 0)  # mcseOffset
        header[76:80] = struct.pack('<I', 0)  # nSndEmitters
        header[80:84] = struct.pack('<I', mclq_offset)
        header[84:88] = struct.pack('<I', mclq_size)
        header[88:92] = struct.pack('<f', -10000)  # posY
        header[92:96] = struct.pack('<f', -10000)  # posX
        header[96:100] = struct.pack('<f', 0)  # posZ
        header[100:104] = struct.pack('<I', 0)  # mccvOffset
        header[104:108] = struct.pack('<I', 0)  # mclvOffset
        header[108:112] = struct.pack('<I', 0)  # unused

        # Build chunk data with subchunks
        data = bytearray()
        data.extend(header)  # Header
        data.extend(b'\0' * 8)  # Padding to align with retail

        # MCVT (required)
        data.extend(b'TVCM')
        data.extend(struct.pack('<I', 580))
        data.extend(self.mcvt_data)

        # MCNR (required)
        data.extend(b'RNCM')
        data.extend(struct.pack('<I', 448))
        data.extend(self.mcnr_data)

        # MCLY (only if we have layers)
        if has_mcly:
            data.extend(b'YLCM')
            data.extend(struct.pack('<I', len(self.mcly_data)))
            data.extend(self.mcly_data)

        # MCRF (only if we have doodads or WMOs)
        if has_mcrf:
            data.extend(b'FRCM')
            data.extend(struct.pack('<I', len(self.mcrf_data)))
            data.extend(self.mcrf_data)

        # MCSH (only if has_mcsh flag is set)
        if has_mcsh:
            data.extend(b'HSCM')
            data.extend(struct.pack('<I', mcsh_size))
            data.extend(self.mcsh_data)

        # MCAL (only if we have alpha data)
        if has_mcal:
            data.extend(b'LACM')
            data.extend(struct.pack('<I', len(self.mcal_data)))
            data.extend(self.mcal_data)

        # MCLQ (only if we have liquid flags)
        if has_mclq:
            data.extend(b'QLCM')
            data.extend(struct.pack('<I', len(self.mclq_data)))
            data.extend(self.mclq_data)

        return Chunk(letters='KNCM', size=len(data) - 8, data=bytes(data))  # Subtract padding from size