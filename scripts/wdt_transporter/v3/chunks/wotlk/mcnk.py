"""MCNK chunk handling for WotLK WoW files."""
from dataclasses import dataclass
import struct
from typing import List, Optional, Tuple

from ..base import Chunk


@dataclass
class WotlkAdtCell:
    """ADT cell in WotLK WDT files.
    
    This represents a single cell in the 64x64 grid of ADT files.
    The flags field indicates whether the ADT exists (1) or not (0).
    """
    flags: int = 0

    def to_bytes(self) -> bytes:
        """Convert cell to bytes for writing to file.
        
        The cell is stored as a 32-bit integer containing the flags.
        """
        return struct.pack('<I', self.flags)


@dataclass
class McnkChunk:
    """MCNK (terrain) chunk from WotLK WDT files.
    
    This follows the structure from gp/wowfiles/ChunkHeaders.h McnkHeader.
    Key differences from Alpha:
    - Uses raw chunk names (e.g. 'KNCM' not 'MCNK')
    - Additional fields for WotLK format
    - Different subchunk order
    """
    flags: int = 0
    ix: int = 0
    iy: int = 0
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
    pred_tex: int = 0
    n_effect_doodad: int = 0
    mcse_offset: int = 0
    n_snd_emitters: int = 0
    mclq_offset: int = 0
    mclq_size: int = 0
    pos_y: float = 0.0
    pos_x: float = 0.0
    pos_z: float = 0.0
    mccv_offset: int = 0
    mclv_offset: int = 0
    unused: int = 0
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
        (flags, ix, iy, n_layers, n_doodad_refs,
         mcvt_offset, mcnr_offset, mcly_offset, mcrf_offset,
         mcal_offset, mcal_size, mcsh_offset, mcsh_size,
         area_id, n_mapobj_refs, holes,
         pred_tex, n_effect_doodad, mcse_offset, n_snd_emitters,
         mclq_offset, mclq_size,
         pos_y, pos_x, pos_z,
         mccv_offset, mclv_offset, unused,
         _pad1, _pad2, _pad3, _pad4) = struct.unpack('<4I6I4I3I2I3f3I4I', header)

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
        mclq_data = data[mclq_offset:mclq_offset + mclq_size] if mclq_size > 0 else b''

        return cls(
            flags=flags,
            ix=ix,
            iy=iy,
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
            pred_tex=pred_tex,
            n_effect_doodad=n_effect_doodad,
            mcse_offset=mcse_offset,
            n_snd_emitters=n_snd_emitters,
            mclq_offset=mclq_offset,
            mclq_size=mclq_size,
            pos_y=pos_y,
            pos_x=pos_x,
            pos_z=pos_z,
            mccv_offset=mccv_offset,
            mclv_offset=mclv_offset,
            unused=unused,
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

    def __str__(self) -> str:
        return f"MCNK Chunk ({self.ix}, {self.iy})"