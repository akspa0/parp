from construct import Struct, Int32ul, Float32l, Array, GreedyBytes

# Global Chunk Decoders

global_chunk_decoders = {}

# NICM Chunk Decoder (Pointers to MCNK chunks and their sizes)
NICM = Struct(
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
global_chunk_decoders["NICM"] = NICM

# RDHM Chunk Decoder
RDHM = Struct(
    "flags" / Int32ul,
    "mcin" / Int32ul,
    "mtex" / Int32ul,
    "mmdx" / Int32ul,
    "mmid" / Int32ul,
    "mwmo" / Int32ul,
    "mwid" / Int32ul,
    "fddm" / Int32ul,  # Updated from mddf
    "modf" / Int32ul,
    "mfbo" / Int32ul,
    "mh2o" / Int32ul,
    "mtxf" / Int32ul,
    "mamp_value" / Int32ul,
    "padding" / Array(3, Int32ul),
    "unused" / GreedyBytes  # Adjusted to accommodate variable length or missing data
)
global_chunk_decoders["RDHM"] = RDHM

# FDDM Chunk Decoder (Model Definitions)
FDDM = Struct(
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
global_chunk_decoders["FDDM"] = FDDM

# KNCM Chunk Decoder (Handles MCNK sub-chunks)
KNCM = Struct(
    "header" / Struct(
        "flags" / Int32ul,
        "index_x" / Int32ul,
        "index_y" / Int32ul,
        "layer_count" / Int32ul,
        "doodad_count" / Int32ul,
        "offsets" / Array(8, Int32ul)
    ),
    "sub_chunks" / GreedyBytes
)

def decode_kncm_sub_chunks(sub_chunks_data, offsets):
    """
    Decode sub-chunks within a KNCM (MCNK) chunk.

    :param sub_chunks_data: Byte data containing all sub-chunks.
    :param offsets: Offsets from the KNCM header pointing to sub-chunk locations.
    :return: A dictionary of decoded sub-chunks.
    """
    sub_chunks = {}
    for offset in offsets:
        if offset == 0 or offset >= len(sub_chunks_data):
            continue  # Skip invalid offsets

        # Read sub-chunk header
        subchunk_id_bytes = sub_chunks_data[offset:offset + 4]
        subchunk_id = subchunk_id_bytes[::-1].decode("utf-8", errors="replace").strip()  # Reverse the ID
        subchunk_size = int.from_bytes(sub_chunks_data[offset + 4:offset + 8], "little")
        subchunk_data_start = offset + 8
        subchunk_data_end = subchunk_data_start + subchunk_size

        # Validate sub-chunk size
        if subchunk_data_end > len(sub_chunks_data):
            logger.warning(f"Sub-chunk {subchunk_id} at offset {offset} exceeds data boundaries.")
            continue

        # Extract and decode sub-chunk data
        subchunk_data = sub_chunks_data[subchunk_data_start:subchunk_data_end]
        if subchunk_id in kncm_subchunk_decoders:
            decoder = kncm_subchunk_decoders[subchunk_id]
            try:
                sub_chunks[subchunk_id] = decoder.parse(subchunk_data)
            except Exception as e:
                logger.error(f"Error decoding sub-chunk {subchunk_id}: {e}")
                sub_chunks[subchunk_id] = {"error": str(e), "raw_data": subchunk_data.hex()}
        else:
            logger.warning(f"No decoder available for sub-chunk ID {subchunk_id}. Logging raw data.")
            sub_chunks[subchunk_id] = {"raw_data": subchunk_data.hex()}

    return sub_chunks

global_chunk_decoders["KNCM"] = KNCM

# Placeholder Decoders for Unknown Chunks
DIMM = Struct(
    "data" / GreedyBytes
)
global_chunk_decoders["DIMM"] = DIMM

DIWM = Struct(
    "data" / GreedyBytes
)
global_chunk_decoders["DIWM"] = DIWM

FDOM = Struct(
    "data" / GreedyBytes
)
global_chunk_decoders["FDOM"] = FDOM
