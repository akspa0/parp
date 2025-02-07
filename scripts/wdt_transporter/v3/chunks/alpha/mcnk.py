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
    adt_x: int = 0           # ADT X coordinate (0-63)
    adt_y: int = 0           # ADT Y coordinate (0-63)

    @classmethod
    def from_chunk(cls, chunk: Chunk, adt_x: int, adt_y: int) -> 'McnkChunk':
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
            mclq_data=mclq_data,
            adt_x=adt_x,
            adt_y=adt_y
        )

    def to_wotlk(self) -> Chunk:
        """Convert to WotLK format.
        
        Following gp/wowfiles/alpha/McnkAlpha.cpp toMcnkLk() implementation:
        - Copy basic fields from alpha header
        - Add new fields for WotLK format
        - Preserve subchunk data with proper offsets
        """
        # Calculate subchunk offsets including chunk headers (8 bytes each)
        base_offset = 128  # Start after MCNK header
        mcvt_offset = base_offset  # MCVT starts immediately after header
        mcnr_offset = mcvt_offset + 8 + 580  # MCVT header + data
        mcly_offset = mcnr_offset + 8 + 448  # MCNR header + data

        # MCLY (only if we have layers)
        has_mcly = bool(self.n_layers > 0 and self.mcly_data)
        if not has_mcly:
            mcly_offset = 0

        # MCRF (only if we have doodads or WMOs)
        has_mcrf = bool((self.n_doodad_refs > 0 or self.n_mapobj_refs > 0) and self.mcrf_data)
        mcrf_offset = mcly_offset + (8 + len(self.mcly_data) if has_mcly else 0)
        if not has_mcrf:
            mcrf_offset = 0

        # MCSH comes before MCAL in retail
        has_mcsh = bool(self.flags & 0x1 and self.mcsh_data)  # Check has_mcsh flag
        mcsh_offset = mcrf_offset + (8 + len(self.mcrf_data) if has_mcrf else 0)
        mcsh_size = len(self.mcsh_data) if has_mcsh else 0
        if not has_mcsh:
            mcsh_offset = 0

        # MCAL comes after MCSH
        has_mcal = bool(self.mcal_size > 0 and self.mcal_data)  # Check size in header
        mcal_offset = mcsh_offset + (8 + len(self.mcsh_data) if has_mcsh else 0)
        mcal_size = len(self.mcal_data) + 8 if has_mcal else 0  # Include header size
        if not has_mcal:
            mcal_offset = 0

        # MCLQ (only if we have liquid flags)
        has_mclq = bool(self.flags & 0x0E and self.mclq_data)  # Check liquid flags (ocean/river/magma)
        mclq_offset = mcal_offset + (8 + len(self.mcal_data) if has_mcal else 0)
        if has_mclq:
            # Calculate MCLQ size as remaining data after offset
            mclq_size = len(self.mclq_data) + 8  # Include header size
            # Add MCLQ data size to total subchunks size
            subchunks_size += 8 + len(self.mclq_data)  # header (8) + data
        else:
            mclq_offset = 0
            mclq_size = 0

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

        # Calculate ADT position
        pos_y = ((((533.33333 / 16) * self.ix) + (533.33333 * self.adt_x)) - (533.33333 * 32)) * -1
        pos_x = ((((533.33333 / 16) * self.iy) + (533.33333 * self.adt_y)) - (533.33333 * 32)) * -1

        header[88:92] = struct.pack('<f', pos_y)  # posY
        header[92:96] = struct.pack('<f', pos_x)  # posX
        header[96:100] = struct.pack('<f', 0)  # posZ
        header[100:104] = struct.pack('<I', 0)  # mccvOffset
        header[104:108] = struct.pack('<I', 0)  # mclvOffset
        header[108:112] = struct.pack('<I', 0)  # unused

        # Calculate total size of all subchunks (including their headers)
        subchunks_size = 0

        # Helper to calculate subchunk size including header
        def subchunk_size(chunk_data: bytes) -> int:
            return 8 + len(chunk_data)  # header (8) + data

        # Add required chunks
        subchunks_size += subchunk_size(self.mcvt_data)  # MCVT (580 + 8)
        subchunks_size += subchunk_size(self.mcnr_data)  # MCNR (448 + 8)

        # Add optional chunks
        if has_mcly:
            subchunks_size += subchunk_size(self.mcly_data)  # MCLY
        if has_mcrf:
            subchunks_size += subchunk_size(self.mcrf_data)  # MCRF
        if has_mcsh:
            subchunks_size += subchunk_size(self.mcsh_data)  # MCSH
        if has_mcal:
            subchunks_size += subchunk_size(self.mcal_data)  # MCAL
        if has_mclq:
            subchunks_size += subchunk_size(self.mclq_data)  # MCLQ

        # Update mcnkChunksSize in header (at offset 0x5C)
        header[0x5C:0x60] = struct.pack('<I', subchunks_size)

        # Build chunk data
        data = bytearray()
        data.extend(header)  # Header (128 bytes)

        # Helper to write subchunk
        def write_subchunk(letters: bytes, chunk_data: bytes) -> None:
            data.extend(letters)  # 4 bytes magic
            data.extend(struct.pack('<I', len(chunk_data)))  # 4 bytes size
            data.extend(chunk_data)  # chunk data

        # Write subchunks in order
        write_subchunk(b'TVCM', self.mcvt_data)  # MCVT (required)
        write_subchunk(b'RNCM', self.mcnr_data)  # MCNR (required)

        if has_mcly:
            write_subchunk(b'YLCM', self.mcly_data)
        if has_mcrf:
            write_subchunk(b'FRCM', self.mcrf_data)
        if has_mcsh:
            write_subchunk(b'HSCM', self.mcsh_data)
        if has_mcal:
            write_subchunk(b'LACM', self.mcal_data)
        if has_mclq:
            write_subchunk(b'QLCM', self.mclq_data)

        # Create chunk with total size
        # Size should be subchunks_size + 128 (MCNK header)
        # This matches the C++ implementation where:
        # - mcnkChunksSize is subchunks_size (all subchunks with headers)
        # - givenSize is subchunks_size + 128 (all data including MCNK header)
        # - chunk header (8 bytes) is not included in size
        return Chunk(letters='KNCM', size=subchunks_size + 128, data=bytes(data))

        # Build chunk data
        data = bytearray()
        data.extend(header)  # Header (128 bytes)

        # Helper to write subchunk
        def write_subchunk(letters: bytes, chunk_data: bytes) -> None:
            data.extend(letters)  # 4 bytes magic
            data.extend(struct.pack('<I', len(chunk_data)))  # 4 bytes size
            data.extend(chunk_data)  # chunk data

        # Write subchunks in order
        write_subchunk(b'TVCM', self.mcvt_data)  # MCVT (required)
        write_subchunk(b'RNCM', self.mcnr_data)  # MCNR (required)

        if has_mcly:
            write_subchunk(b'YLCM', self.mcly_data)
        if has_mcrf:
            write_subchunk(b'FRCM', self.mcrf_data)
        if has_mcsh:
            write_subchunk(b'HSCM', self.mcsh_data)
        if has_mcal:
            write_subchunk(b'LACM', self.mcal_data)
        if has_mclq:
            write_subchunk(b'QLCM', self.mclq_data)

        # Create chunk with data only (no header)
        return Chunk(letters='KNCM', size=len(data), data=bytes(data))

    def __str__(self) -> str:
        return f"MCNK Chunk ({self.ix}, {self.iy})"