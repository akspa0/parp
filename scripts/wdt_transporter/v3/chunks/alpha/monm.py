"""MONM chunk handling for Alpha WoW files."""
from dataclasses import dataclass
from typing import List

from ..base import Chunk


@dataclass
class MonmChunk:
    """MONM (WMO filenames) chunk from Alpha WDT files.
    
    This chunk contains a list of WMO filenames, each null-terminated.
    The filenames are used to create the MWMO and MWID chunks in WotLK format.
    """
    filenames: List[str]

    @classmethod
    def from_chunk(cls, chunk: Chunk) -> 'MonmChunk':
        """Create MONM chunk from raw chunk data."""
        if chunk.letters != 'MNOM':
            raise ValueError(f"Expected MNOM chunk, got {chunk.letters}")

        # Split data on null bytes, filter out empty strings
        filenames = [
            name.decode('ascii')
            for name in chunk.data.split(b'\0')
            if name  # Filter out empty strings
        ]

        return cls(filenames=filenames)

    def __str__(self) -> str:
        return f"MONM Chunk ({len(self.filenames)} filenames)"