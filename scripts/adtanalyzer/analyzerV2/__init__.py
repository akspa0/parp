"""
WoW Terrain Analyzer V2
A refactored and improved version of the WoW terrain file analyzer.
"""

__version__ = '2.0.0'
__author__ = 'Roo'
__description__ = 'World of Warcraft Terrain File Analyzer'

from .modules.parsers import ADTParser, WDTParser
from .modules.models import TerrainFile, ADTFile, WDTFile
from .modules.database import DatabaseManager
from .modules.json import JSONHandler

__all__ = [
    'ADTParser',
    'WDTParser',
    'TerrainFile',
    'ADTFile',
    'WDTFile',
    'DatabaseManager',
    'JSONHandler',
]