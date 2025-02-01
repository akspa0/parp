# adt_format.py

from construct import (
    Struct, 
    Bytes, 
    Int32ul, 
    Int16ul, 
    Float32l, 
    Adapter, 
    CString,
    Array,
    Tell,
    Pass,
    Const,
    Padding
)
from typing import NamedTuple
import logging

logger = logging.getLogger(__name__)

class Vec3D(NamedTuple):
    x: float
    y: float
    z: float

# Utility adapters
class Vec3DAdapter(Adapter):
    def _decode(self, obj, context, path):
        return Vec3D(x=obj[0], y=obj[1], z=obj[2])
    
    def _encode(self, obj, context, path):
        return [obj.x, obj.y, obj.z]

# Common structures
Vec3DFloat = Vec3DAdapter(Float32l[3])

# Chunk header structure
ChunkHeader = Struct(
    "magic" / Bytes(4),
    "size" / Int32ul,
)

# MVER chunk
MVERChunk = Struct(
    "header" / ChunkHeader,
    "version" / Int32ul,
)

# MHDR chunk
MHDRChunk = Struct(
    "header" / ChunkHeader,
    "flags" / Int32ul,
    "mcin_offset" / Int32ul,
    "mtex_offset" / Int32ul,
    "mmdx_offset" / Int32ul,
    "mmid_offset" / Int32ul,
    "mwmo_offset" / Int32ul,
    "mwid_offset" / Int32ul,
    "mddf_offset" / Int32ul,
    "modf_offset" / Int32ul,
    "mfbo_offset" / Int32ul,
    "mh2o_offset" / Int32ul,
    "mtxf_offset" / Int32ul,
    Padding(8),  # Unused fields at the end
)

# MCIN chunk - cell information
MCINEntry = Struct(
    "offset" / Int32ul,
    "size" / Int32ul,
    "flags" / Int32ul,
    "async_id" / Int32ul,
)

MCINChunk = Struct(
    "header" / ChunkHeader,
    "entries" / Array(256, MCINEntry),
)

# MTEX chunk - texture list
MTEXChunk = Struct(
    "header" / ChunkHeader,
    "textures" / CString("utf8")[lambda ctx: ctx.header.size],
)

# MMDX/MWMO chunk - model filename list
ModelListChunk = Struct(
    "header" / ChunkHeader,
    "data" / Bytes(lambda ctx: ctx.header.size),
)

# MMID/MWID chunk - filename offsets
OffsetListChunk = Struct(
    "header" / ChunkHeader,
    "offsets" / Int32ul[lambda ctx: ctx.header.size // 4],
)

# MDDF chunk - M2 model placements
MDDFEntry = Struct(
    "nameId" / Int32ul,
    "uniqueId" / Int32ul,
    "position" / Vec3DFloat,
    "rotation" / Vec3DFloat,
    "scale" / Int16ul,
    "flags" / Int16ul,
)

MDDFChunk = Struct(
    "header" / ChunkHeader,
    "entries" / MDDFEntry[lambda ctx: ctx.header.size // 36],
)

# MODF chunk - WMO placements
MODFEntry = Struct(
    "nameId" / Int32ul,
    "uniqueId" / Int32ul,
    "position" / Vec3DFloat,
    "rotation" / Vec3DFloat,
    "extents_lower" / Vec3DFloat,
    "extents_upper" / Vec3DFloat,
    "flags" / Int16ul,
    "doodadSet" / Int16ul,
    "nameSet" / Int16ul,
    "scale" / Int16ul,
)

MODFChunk = Struct(
    "header" / ChunkHeader,
    "entries" / MODFEntry[lambda ctx: ctx.header.size // 64],
)

# MCNK chunk - map chunk
MCNKFlags = Struct(
    "has_mcsh" / Int32ul,
    "impass" / Int32ul,
    "lq_water" / Int32ul,
    "has_mccv" / Int32ul,
)

MCNKLayers = Struct(
    "layer_count" / Int32ul,
    "data_size" / Int32ul,
)

MCNKChunk = Struct(
    "header" / ChunkHeader,
    "flags" / MCNKFlags,
    "ix" / Int32ul,
    "iy" / Int32ul,
    "layer_count" / Int32ul,
    "doodad_refs" / Int32ul,
    "offset_mcvt" / Int32ul,
    "offset_mcnr" / Int32ul,
    "offset_mcly" / Int32ul,
    "offset_mcrf" / Int32ul,
    "offset_mcal" / Int32ul,
    "size_mcal" / Int32ul,
    "offset_mcsh" / Int32ul,
    "size_mcsh" / Int32ul,
    "area_id" / Int32ul,
    "map_object_refs" / Int32ul,
    "holes" / Int32ul,
    "low_quality_texture_map" / Int16ul[8],
    "predTex" / Int32ul,
    "noEffectDoodad" / Int32ul,
    "offset_mcse" / Int32ul,
    "sound_emitters_count" / Int32ul,
    "offset_mclq" / Int32ul,
    "size_mclq" / Int32ul,
    "position" / Vec3DFloat,
    "offset_mccv" / Int32ul,
)

def read_chunk_header(data: bytes, offset: int = 0) -> tuple[bytes, int]:
    """Read a chunk header from the given data at the specified offset."""
    try:
        header = ChunkHeader.parse(data[offset:offset+8])
        return header.magic, header.size
    except Exception as e:
        logger.error(f"Failed to parse chunk header at offset {offset}: {e}")
        return None, 0

def parse_string_list_from_offsets(data: bytes, offsets: list[int]) -> list[str]:
    """Parse a list of null-terminated strings from the given data using offsets."""
    strings = []
    for offset in offsets:
        if offset >= len(data):
            strings.append("<invalid offset>")
            continue
        try:
            end = data.find(b'\0', offset)
            if end == -1:
                string = data[offset:].decode('utf-8', 'replace')
            else:
                string = data[offset:end].decode('utf-8', 'replace')
            strings.append(string)
        except Exception as e:
            logger.error(f"Failed to decode string at offset {offset}: {e}")
            strings.append("<decode error>")
    return strings
