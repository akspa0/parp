"""NIAM (MAIN) chunk from Alpha WDT files."""
from dataclasses import dataclass
from typing import List, Tuple
import struct
from ..base import Chunk


@dataclass
class AdtCell:
    """Information about an ADT cell in the 64x64 grid.
    
    This follows the structure from gp/wowfiles/alpha/MainAlpha.h
    but simplified to just handle the cell data.
    """
    offset: int = 0      # Absolute offset from start of file
    size: int = 0        # Size of ADT data
    flags: int = 0       # Unused in alpha
    padding: bytes = b'\x00' * 4  # 4 bytes padding


@dataclass
class NiamChunk:
    """NIAM chunk containing ADT cell information.
    
    The chunk contains a 64x64 grid of ADT cells, where each cell
    contains information about the ADT file for that grid position.
    """
    cells: List[List[AdtCell]]  # 64x64 grid of ADT cells

    @classmethod
    def from_chunk(cls, chunk: Chunk) -> 'NiamChunk':
        """Create NIAM chunk from raw chunk data."""
        if chunk.letters != 'NIAM':
            raise ValueError(f"Expected NIAM chunk, got {chunk.letters}")

        if chunk.size != 64 * 64 * 16:  # 64x64 grid, 16 bytes per cell
            raise ValueError(f"Expected size {64*64*16} for NIAM chunk, got {chunk.size}")

        cells = []
        for y in range(64):
            row = []
            for x in range(64):
                offset = (y * 64 + x) * 16
                cell_data = chunk.data[offset:offset+16]
                cell = AdtCell(
                    offset=struct.unpack('<I', cell_data[0:4])[0],
                    size=struct.unpack('<I', cell_data[4:8])[0],
                    flags=struct.unpack('<I', cell_data[8:12])[0],
                    padding=cell_data[12:16]
                )
                row.append(cell)
            cells.append(row)

        return cls(cells=cells)

    def to_chunk(self) -> Chunk:
        """Convert to raw chunk format."""
        data = bytearray()
        for row in self.cells:
            for cell in row:
                data.extend(struct.pack('<I', cell.offset))
                data.extend(struct.pack('<I', cell.size))
                data.extend(struct.pack('<I', cell.flags))
                data.extend(cell.padding)
        return Chunk(letters='NIAM', size=64*64*16, data=bytes(data))

    def get_adt_cells(self) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Get list of ((x,y), (offset,size)) tuples for existing ADTs.
        
        Returns a list of tuples containing:
        - Grid position as (x,y) tuple
        - ADT data as (offset,size) tuple
        
        Only returns cells that have valid ADT data (offset > 0).
        List is sorted by offset to maintain file order.
        """
        adt_cells = []
        for y in range(64):
            for x in range(64):
                cell = self.cells[y][x]
                if cell.offset > 0 and cell.size > 0:
                    adt_cells.append(((x, y), (cell.offset, cell.size)))
        return sorted(adt_cells, key=lambda x: x[1][0])  # Sort by offset

    def __str__(self) -> str:
        adt_count = sum(1 for row in self.cells 
                       for cell in row if cell.offset > 0 and cell.size > 0)
        return f"NIAM Chunk ({adt_count} ADT cells)"