from construct import Struct, Int32ul, Float32l, GreedyBytes, Array, PrefixedArray

# Define chunk structures using `construct`
REVM = Struct(
    "version" / Int32ul
)

XETM = Struct(
    "textures" / GreedyBytes  # To be split into strings later
)

XDMM = Struct(
    "MMDX_block" / GreedyBytes
)

OMWM = Struct(
    "MWMO_block" / GreedyBytes
)

NICM = Struct(
    "entries" / Array(
        lambda this: this._.chunk_size // 16,  # Calculate number of entries dynamically
        Struct(
            "offset" / Int32ul,
            "size" / Int32ul,
            "flags" / Int32ul,
            "unused" / Int32ul,
        )
    )
)

FDMD = Struct(
    "entries" / Array(
        lambda this: len(this._io) // 36,  # Calculate number of entries
        Struct(
            "nameId" / Int32ul,
            "uniqueId" / Int32ul,
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

YLCK = Struct(
    "layers" / Array(
        lambda this: len(this._io) // 16,  # Calculate number of layers
        Struct(
            "textureId" / Int32ul,
            "flags" / Int32ul,
            "offsetInMCAL" / Int32ul,
            "effectId" / Int32ul,
        )
    )
)

RNCM = Struct(
    "normals" / Array(
        lambda this: len(this._io) // 12,  # Each normal is 12 bytes
        Struct(
            "x" / Float32l,
            "y" / Float32l,
            "z" / Float32l,
        )
    )
)

LACM = Struct(
    "MCAL_data" / GreedyBytes
)

HSCK = Struct(
    "shadow_map" / Array(
        lambda this: len(this._io),  # Each byte is a shadow map value
        Int32ul
    )
)

KNCM = Struct(
    "header" / Struct(
        "flags" / Int32ul,
        "index_x" / Int32ul,
        "index_y" / Int32ul,
        "layer_count" / Int32ul,
        "doodad_count" / Int32ul,
        "offsets" / Array(8, Int32ul),  # Sub-chunk offsets
    ),
    "chunk_size" / Int32ul,  # Add chunk size here
    "sub_chunks" / GreedyBytes,  # Placeholder for processing sub-chunks
)

# Decoder mapping directly with ADT file chunk IDs
adt_chunk_decoders = {
    'REVM': REVM,  # MVER
    'XETM': XETM,  # MTEX
    'XDMM': XDMM,  # MMDX
    'OMWM': OMWM,  # MWMO
    'NICM': NICM,  # MCIN
    'FDMD': FDMD,  # MDDF
    'YLCK': YLCK,  # MCLY
    'RNCM': RNCM,  # MCNR
    'LACM': LACM,  # MCAL
    'HSCK': HSCK,  # MCSH
    'KNCM': KNCM,  # MCNK
}

# Parse a chunk using `construct`
def parse_chunk(chunk_id, data, chunk_size=None):
    decoder = adt_chunk_decoders.get(chunk_id)
    if decoder:
        return decoder.parse(data, chunk_size=chunk_size)
    else:
        raise ValueError(f"No decoder available for chunk ID {chunk_id}")
