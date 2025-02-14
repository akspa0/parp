# adt_analyzer/chunks/mhdr/flags.py
from enum import IntFlag, auto

class MhdrFlags(IntFlag):
    """Flags used in MHDR chunk."""
    HAS_MFBO = auto()          # Contains flight box
    HAS_MH2O = auto()          # Contains MH2O chunk (water)
    HAS_MTXF = auto()          # Contains MTXF chunk (texture flags)
    USE_BIG_ALPHA = auto()     # Use 4096 bytes for MCAL instead of 2048
    USE_BIG_TEXTURES = auto()  # High-res textures
    USE_MCSH = auto()          # Contains MCSH chunk (shadows)
    UNUSED_6 = auto()
    UNUSED_7 = auto()
