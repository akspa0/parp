from construct import Struct, Int32ul, Float32l, GreedyBytes, Array, CString, If
from object_decoders import MDDF  # Import the specific decoder

# MCIN Chunk Decoder
MCIN = Struct(
    "entries" / Array(
        16 * 16,  # 16x16 grid of MCNK chunks
        Struct(
            "offset" / Int32ul,  # Absolute offset of the MCNK chunk
            "size" / Int32ul,    # Size of the MCNK chunk
            "flags" / Int32ul,   # Flags, usually 0
            "pad" / Int32ul      # Padding or client-side async ID
        )
    )
)

# RDHM Chunk Decoder
RDHM = Struct(
    "flags" / Int32ul,
    "mcin" / Int32ul,  # Offset to MCIN
    "mtex" / Int32ul,  # Offset to MTEX
    "mmdx" / Int32ul,  # Offset to MMDX
    "mmid" / Int32ul,  # Offset to MMID
    "mwmo" / Int32ul,  # Offset to MWMO
    "mwid" / Int32ul,  # Offset to MWID
    "mddf" / Int32ul,  # Offset to MDDF
    "modf" / Int32ul,  # Offset to MODF
    "mfbo" / Int32ul,  # Offset to MFBO (only if flags indicate)
    "mh2o" / Int32ul,  # Offset to MH2O
    "mtxf" / Int32ul,  # Offset to MTXF
    "mamp_value" / Int32ul,  # Cata+: explicit MAMP chunk overrides data
    "padding" / Array(3, Int32ul),
    "unused" / If(lambda this: this._io.tell() + 12 <= len(this._io.getvalue()), Array(3, Int32ul))
)

# MWMO Chunk Decoder (World Map Objects)
MWMO = Struct(
    "file_names" / GreedyBytes  # Null-terminated WMO file names
)

# Add to global decoders
global_chunk_decoders = {
    "MCIN": MCIN,
    "RDHM": RDHM,
    "MWMO": MWMO,
    'MDDF': MDDF,
}
