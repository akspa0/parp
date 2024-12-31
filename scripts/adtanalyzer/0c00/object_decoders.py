from construct import Struct, Int32ul, Float32l, Array

# Object-related sub-chunks
MDDF = Struct(
    "entries" / Array(
        lambda this: len(this._io) // 36,
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

object_decoders = {
    'MDDF': MDDF,
}
