import logging
from construct import Struct, Int32ul, Float32l, Array, GreedyBytes, BitStruct, Flag, Padding, IfThenElse

logger = logging.getLogger("mcnk_chunk_decoder")

# Define the MCNK Header with dynamic fields based on flags
MCNK_Header = Struct(
    "flags" / BitStruct(
        "has_mcsh" / Flag,
        "impass" / Flag,
        "lq_river" / Flag,
        "lq_ocean" / Flag,
        "lq_magma" / Flag,
        "lq_slime" / Flag,
        "has_mccv" / Flag,
        "unknown_0x80" / Flag,
        Padding(7),
        "do_not_fix_alpha_map" / Flag,
        "high_res_holes" / Flag,
        Padding(15)
    ),
    "index_x" / Int32ul,
    "index_y" / Int32ul,
    "n_layers" / Int32ul,
    "n_doodad_refs" / Int32ul,
    "holes_high_res" / IfThenElse(lambda this: this.flags.high_res_holes, Int32ul, Padding(4)),
    "ofs_height" / Int32ul,
    "ofs_normal" / Int32ul,
    "ofs_layer" / Int32ul,
    "ofs_refs" / Int32ul,
    "ofs_alpha" / Int32ul,
    "size_alpha" / Int32ul,
    "ofs_shadow" / IfThenElse(lambda this: this.flags.has_mcsh, Int32ul, Padding(4)),
    "size_shadow" / IfThenElse(lambda this: this.flags.has_mcsh, Int32ul, Padding(4)),
    "area_id" / Int32ul,
    "n_map_obj_refs" / Int32ul,
    "holes_low_res" / Int32ul,
    "unknown_but_used" / Int32ul,
    "pred_tex" / Array(8, Array(8, Int32ul)),
    "no_effect_doodad" / Array(8, Array(8, Int32ul)),
    "ofs_snd_emitters" / Int32ul,
    "n_snd_emitters" / Int32ul,
    "ofs_liquid" / Int32ul,
    "size_liquid" / Int32ul,
    "position" / Struct(
        "x" / Float32l,
        "y" / Float32l,
        "z" / Float32l,
    ),
    "ofs_mccv" / IfThenElse(lambda this: this.flags.has_mccv, Int32ul, Padding(4)),
    "ofs_mclv" / Int32ul,
    "unused" / Int32ul,
)

# Define MCNK Subchunk Decoders
MCNK_Subchunk_Decoders = {
    "MCVT": Struct("heights" / Array(145, Float32l)),
    "MCNR": Struct("normals" / Array(145, Struct("x" / Float32l, "y" / Float32l, "z" / Float32l))),
    "MCLY": Struct("layers" / GreedyBytes),
    "MCAL": Struct("alphamaps" / GreedyBytes),
    "MCSH": Struct("shadowmap" / GreedyBytes),
    "MCSE": Struct("sound_emitters" / GreedyBytes),
    "MCLQ": Struct(
        "flags" / Int32ul,
        "heights" / Array(81, Float32l),
        "attributes" / GreedyBytes
    ),
}

def parse_mcnk_subchunk(subchunk_id, data):
    """Parse a specific MCNK subchunk."""
    decoder = MCNK_Subchunk_Decoders.get(subchunk_id)
    if decoder:
        try:
            return decoder.parse(data)
        except Exception as e:
            logger.error(f"Error decoding subchunk {subchunk_id}: {e}")
            return {"error": str(e), "raw_data": data.hex()}
    else:
        logger.warning(f"No decoder available for subchunk ID {subchunk_id}. Logging raw data.")
        return {"raw_data": data.hex()}

def decode_mcnk_chunk(mcnk_data):
    """
    Decode a full MCNK chunk, including header and sub-chunks.

    :param mcnk_data: Byte data of the MCNK chunk.
    :return: Decoded MCNK structure with header and sub-chunks.
    """
    try:
        logger.debug(f"Raw MCNK header data (first 128 bytes): {mcnk_data[:128].hex()}")
        # Parse the MCNK header
        header = MCNK_Header.parse(mcnk_data[:128])
        logger.info(f"Decoded MCNK header: {header}")

        # Extract sub-chunks using header offsets
        sub_chunks = {}
        subchunk_data = mcnk_data[128:]
        offsets = {
            "MCVT": header.ofs_height,
            "MCNR": header.ofs_normal,
            "MCLY": header.ofs_layer,
            "MCAL": header.ofs_alpha,
            "MCSH": header.ofs_shadow,
            "MCSE": header.ofs_snd_emitters,
            "MCLQ": header.ofs_liquid,
        }

        for subchunk_id, offset in offsets.items():
            if offset == 0 or offset >= len(subchunk_data):
                continue  # Skip invalid offsets

            try:
                subchunk_size = int.from_bytes(subchunk_data[offset + 4:offset + 8], "little")
                subchunk_content = subchunk_data[offset + 8:offset + 8 + subchunk_size]

                sub_chunks[subchunk_id] = parse_mcnk_subchunk(subchunk_id, subchunk_content)

            except Exception as e:
                logger.error(f"Failed to parse subchunk {subchunk_id} at offset {offset}: {e}")
                sub_chunks[subchunk_id] = {"error": f"Failed to parse subchunk: {e}"}

        return {"header": header, "sub_chunks": sub_chunks}

    except Exception as e:
        logger.error(f"Error decoding MCNK chunk: {e}")
        return {"error": str(e)}
