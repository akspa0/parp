"""NIAM (MAIN) chunk from WotLK WDT files."""
from dataclasses import dataclass
from typing import List, Tuple
import struct
from ..base import Chunk


@dataclass
class AdtCell:
    """Information about an ADT cell in the 64x64 grid.
    
    This follows the structure from gp/wowfiles/lichking/WdtLk.h
    but simplified to just handle the cell data.
    """
    flags: int = 0      # Cell flags (32 bits)

    def to_bytes(self) -> bytes:
        """Convert to raw bytes."""
        return struct.pack('<I', self.flags)


@dataclass
class NiamChunk:
    """NIAM chunk containing ADT cell information.
    
    The chunk contains a 64x64 grid of ADT cells, where each cell
    contains information about that grid position.
    """
    cells: List[List[AdtCell]]  # 64x64 grid of ADT cells

    @classmethod
    def from_chunk(cls, chunk: Chunk) -> 'NiamChunk':
        """Create NIAM chunk from raw chunk data."""
        if chunk.letters != 'NIAM':
            raise ValueError(f"Expected NIAM chunk, got {chunk.letters}")

        if chunk.size != 64 * 64 * 4:  # 64x64 grid, 4 bytes per cell
            raise ValueError(f"Expected size {64*64*4} for NIAM chunk, got {chunk.size}")

        cells = []
        for y in range(64):
            row = []
            for x in range(64):
                offset = (y * 64 + x) * 4
                cell_data = chunk.data[offset:offset+4]
                cell = AdtCell(
                    flags=struct.unpack('<I', cell_data)[0]
                )
                row.append(cell)
            cells.append(row)

        return cls(cells=cells)

    def to_chunk(self) -> Chunk:
        """Convert to raw chunk format."""
        data = bytearray()
        for row in self.cells:
            for cell in row:
                data.extend(cell.to_bytes())
        return Chunk(letters='NIAM', size=64*64*4, data=bytes(data))

    def __str__(self) -> str:
        used_cells = sum(1 for row in self.cells 
                        for cell in row if cell.flags != 0)
        return f"NIAM Chunk ({used_cells} used cells)"