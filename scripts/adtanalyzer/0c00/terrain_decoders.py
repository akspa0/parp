from construct import Struct, Float32l, Array

# Terrain-related sub-chunks
MCVT = Struct(
    "heights" / Array(145, Float32l)  # 145 float values for terrain heights
)

MCNR = Struct(
    "normals" / Array(
        lambda this: len(this._io) // 12,
        Struct(
            "x" / Float32l,
            "y" / Float32l,
            "z" / Float32l,
        )
    )
)

terrain_decoders = {
    'MCVT': MCVT,
    'MCNR': MCNR,
}
