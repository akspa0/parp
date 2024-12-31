from construct import Struct, Int32ul, Float32l, GreedyBytes, Array, CString
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Define additional sub-chunk decoders

# MCNK Sub-chunk: MCVT (Terrain Heights)
MCVT = Struct(
    "heights" / Array(145, Float32l)  # 145 floats for terrain heights
)

# MCNK Sub-chunk: MCLQ (Liquid Data)
MCLQ = Struct(
    "flags" / Int32ul,
    "heights" / Array(81, Float32l),  # 9x9 grid for liquid heights
    "attributes" / GreedyBytes  # Additional liquid attributes
)

# MCNK Sub-chunk: MCSH (Shadow Map)
MCSH = Struct(
    "shadow_map" / GreedyBytes  # Shadow map data
)

# Map sub-chunk IDs to their respective decoders
kncm_subchunk_decoders = {
    "MCVT": MCVT,
    "MCLQ": MCLQ,
    "MCSH": MCSH,
}

def parse_kncm_subchunk(subchunk_id, data):
    """Parse a KNCM/MCNK subchunk."""
    logger.debug(f"Attempting to decode sub-chunk ID: {subchunk_id}")
    decoder = kncm_subchunk_decoders.get(subchunk_id)
    if decoder:
        logger.info(f"Decoding sub-chunk {subchunk_id}")
        return decoder.parse(data)
    else:
        logger.warning(f"No decoder available for subchunk ID {subchunk_id}. Logging raw data.")
        return {"raw_data": data.hex()}
