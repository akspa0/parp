# adt_analyzer/chunks/mcnk/header.py
from dataclasses import dataclass
import struct
from typing import Tuple
from ..base import ChunkParsingError

@dataclass
class McnkHeader:
    """MCNK chunk header structure."""
    flags: int
    ix: int
    iy: int
    n_layers: int
    n_doodad_refs: int
    offset_mcvt: int
    offset_mcnr: int
    offset_mcly: int
    offset_mcrf: int
    offset_mcal: int
    size_mcal: int
    offset_mcsh: int
    size_mcsh: int
    area_id: int
    n_mapobj_refs: int
    holes: int
    layer_texture_id: int
    n_effect_doodad: int
    offset_mcse: int
    n_sound_emitters: int
    offset_mclq: int
    size_mclq: int
    pos: Tuple[float, float, float]
    offset_mccv: int
    offset_mclv: int
    unused: int

    @classmethod
    def from_bytes(cls, data: bytes) -> 'McnkHeader':
        """Parse MCNK header from bytes."""
        try:
            values = struct.unpack('<4I6I4I3I2I3f3I4I', data[:128])
            return cls(
                flags=values[0],
                ix=values[1],
                iy=values[2],
                n_layers=values[3],
                n_doodad_refs=values[4],
                offset_mcvt=values[5],
                offset_mcnr=values[6],
                offset_mcly=values[7],
                offset_mcrf=values[8],
                offset_mcal=values[9],
                size_mcal=values[10],
                offset_mcsh=values[11],
                size_mcsh=values[12],
                area_id=values[13],
                n_mapobj_refs=values[14],
                holes=values[15],
                layer_texture_id=values[16],
                n_effect_doodad=values[17],
                offset_mcse=values[18],
                n_sound_emitters=values[19],
                offset_mclq=values[20],
                size_mclq=values[21],
                pos=(values[22], values[23], values[24]),
                offset_mccv=values[25],
                offset_mclv=values[26],
                unused=values[27]
            )
        except struct.error as e:
            raise ChunkParsingError(f"Failed to parse MCNK header: {e}")
