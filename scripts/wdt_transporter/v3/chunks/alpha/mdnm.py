"""MDNM chunk handling for Alpha WoW files."""
from dataclasses import dataclass
from typing import List

from ..base import Chunk


@dataclass
class MdnmChunk:
    """MDNM (model filenames) chunk from Alpha WDT files.
    
    This chunk contains a list of M2 model filenames, each null-terminated.
    The filenames are used to create the MMDX and MMID chunks in WotLK format.
    """
    filenames: List[str]

    @classmethod
    def from_chunk(cls, chunk: Chunk) -> 'MdnmChunk':
        """Create MDNM chunk from raw chunk data."""
        if chunk.letters != 'MNMD':
            raise ValueError(f"Expected MNMD chunk, got {chunk.letters}")

        # Split data on null bytes, filter out empty strings
        filenames = [
            name.decode('ascii')
            for name in chunk.data.split(b'\0')
            if name  # Filter out empty strings
        ]

        return cls(filenames=filenames)

    def __str__(self) -> str:
        return f"MDNM Chunk ({len(self.filenames)} filenames)"