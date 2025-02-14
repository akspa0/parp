# adt_analyzer/parser/constants.py
from enum import Enum, auto

class ChunkProcessingPhase(Enum):
    """Defines processing phases for ADT chunks."""
    INITIAL = auto()      # MVER, MHDR
    INDICES = auto()      # MCIN
    REFERENCES = auto()   # MTEX, MMDX, MMID, MWMO, MWID
    PLACEMENTS = auto()   # MDDF, MODF
    TERRAIN = auto()      # MCNK and subchunks
