"""
Universal WoW Map File Decoder
"""

from .src.format_detector import FileFormat, FileType, FormatDetector
from .src.base.chunk_parser import ChunkParser, ChunkParsingError
from .src.base.wdt_parser import WDTParserBase
from .src.base.adt_parser import ADTParserBase
from .src.formats.alpha.wdt_parser import AlphaWDTParser
from .src.formats.alpha.adt_parser import AlphaADTParser
from .src.formats.retail.wdt_parser import RetailWDTParser
from .src.formats.retail.adt_parser import RetailADTParser

__version__ = '1.0.0'
__all__ = [
    'FileFormat',
    'FileType',
    'FormatDetector',
    'ChunkParser',
    'ChunkParsingError',
    'WDTParserBase',
    'ADTParserBase',
    'AlphaWDTParser',
    'AlphaADTParser',
    'RetailWDTParser',
    'RetailADTParser'
]