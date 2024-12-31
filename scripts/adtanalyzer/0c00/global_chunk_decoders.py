from construct import Struct, Int32ul, Float32l, GreedyBytes, Array, CString, If

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

# MDDF Chunk Decoder (Model Definitions)
MDDF = Struct(
    "entries" / Array(
        lambda this: len(this._io) // 36,  # Calculate number of entries (36 bytes each)
        Struct(
            "name_id" / Int32ul,  # Reference to model name in MMDX
            "unique_id" / Int32ul,  # Unique identifier
            "position" / Struct(
                "x" / Float32l,
                "y" / Float32l,
                "z" / Float32l,
            ),
            "rotation" / Struct(
                "x" / Float32l,
                "y" / Float32l,
                "z" / Float32l,
            ),
            "scale" / Int32ul,
            "flags" / Int32ul,
        )
    )
)

# MWMO Chunk Decoder (World Map Objects)
MWMO = Struct(
    "file_names" / GreedyBytes  # Null-terminated WMO file names
)

# Add to global decoders
global_chunk_decoders = {
    "RDHM": RDHM,
    "MDDF": MDDF,
    "MWMO": MWMO,
}
