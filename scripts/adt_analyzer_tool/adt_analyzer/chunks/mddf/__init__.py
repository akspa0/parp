# adt_analyzer/chunks/mddf/__init__.py
"""MDDF (M2 Model Placement) parser."""
from .parser import MddfChunk
from .entry import MddfEntry

__all__ = ['MddfChunk', 'MddfEntry']