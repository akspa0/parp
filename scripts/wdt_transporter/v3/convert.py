"""Convert Alpha WDT files to WotLK format."""
import argparse
from datetime import datetime
from pathlib import Path
import struct
from typing import BinaryIO, List, Optional, Tuple
import sys

from chunks.base import Chunk
from chunks import (
    AlphaRevmChunk, AlphaDhpmChunk, AlphaNiamChunk, AlphaAdt,
    WotlkRevmChunk, WotlkDhpmChunk, WotlkNiamChunk, WotlkAdt, WotlkAdtCell
)


def read_alpha_wdt(path: Path) -> Tuple[AlphaRevmChunk, AlphaDhpmChunk, AlphaNiamChunk]:
    """Read an Alpha WDT file and parse its chunks."""
    chunks = {}
    
    with open(path, 'rb') as f:
        while True:
            chunk = Chunk.read(f)
            if not chunk:
                break
            chunks[chunk.letters] = chunk

    # Validate required chunks (in reverse order)
    if 'REVM' not in chunks:
        raise ValueError("Missing REVM chunk")
    if 'DHPM' not in chunks:
        raise ValueError("Missing DHPM chunk")
    if 'NIAM' not in chunks:
        raise ValueError("Missing NIAM chunk")

    # Parse chunks
    revm = AlphaRevmChunk.from_chunk(chunks['REVM'])
    dhpm = AlphaDhpmChunk.from_chunk(chunks['DHPM'])
    niam = AlphaNiamChunk.from_chunk(chunks['NIAM'])

    return revm, dhpm, niam


def write_empty_chunk(f: BinaryIO, letters: str) -> None:
    """Write empty chunk with given letters.
    
    Empty chunks in WDT files have size=4 with zero data.
    """
    data = struct.pack('<I', 0)  # 4 bytes of zeros
    chunk = Chunk(letters=letters, size=4, data=data)
    chunk.write(f)


def write_wotlk_wdt(path: Path, revm: WotlkRevmChunk, dhpm: WotlkDhpmChunk, niam: WotlkNiamChunk) -> None:
    """Write WotLK WDT file."""
    with open(path, 'wb') as f:
        # Write required chunks
        revm.to_chunk().write(f)
        dhpm.to_chunk().write(f)
        niam.to_chunk().write(f)

        # Write empty chunks
        write_empty_chunk(f, 'XDMM')  # MMDX
        write_empty_chunk(f, 'DIMM')  # MMID
        write_empty_chunk(f, 'OMWM')  # MWMO
        write_empty_chunk(f, 'DIWM')  # MWID


def convert_wdt(input_path: Path, output_dir: Path) -> None:
    """Convert Alpha WDT to WotLK format."""
    # Read alpha WDT
    alpha_revm, alpha_dhpm, alpha_niam = read_alpha_wdt(input_path)

    # Convert to WotLK format
    wotlk_revm = WotlkRevmChunk(version=18)  # Always 18 in WotLK
    wotlk_dhpm = WotlkDhpmChunk(flags=1 if alpha_dhpm.is_wmo_based() else 0)

    # Convert NIAM - initialize empty grid
    wotlk_cells = []
    for y in range(64):
        row = []
        for x in range(64):
            alpha_cell = alpha_niam.cells[y][x]
            # Set flags if ADT exists
            flags = 1 if alpha_cell.offset > 0 else 0
            row.append(WotlkAdtCell(flags=flags))
        wotlk_cells.append(row)
    wotlk_niam = WotlkNiamChunk(cells=wotlk_cells)

    # Create map directory
    map_dir = output_dir / input_path.stem
    map_dir.mkdir(exist_ok=True)

    # Write WotLK WDT in map directory
    output_path = map_dir / input_path.name
    write_wotlk_wdt(output_path, wotlk_revm, wotlk_dhpm, wotlk_niam)

    # Convert ADTs
    # Get list of ADTs to convert
    adt_cells = alpha_niam.get_adt_cells()
    if not adt_cells:
        print("No ADTs found in WDT")
        return

    # Convert each ADT
    for (x, y), (offset, size) in adt_cells:
        print(f"Converting ADT {x}_{y}...")
        
        # Read ADT from WDT
        adt_num = y * 64 + x
        alpha_adt = AlphaAdt.read_from_wdt(input_path, offset, adt_num)

        # Convert to WotLK format
        # TODO: Get model/object names from MDNM/MONM chunks
        wotlk_adt = WotlkAdt.from_alpha_adt(alpha_adt, [], [])

        # Write ADT
        adt_name = alpha_adt.get_name(input_path.name)
        adt_path = map_dir / adt_name
        wotlk_adt.write(adt_path)


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description='Convert Alpha WDT files to WotLK format'
    )
    parser.add_argument(
        'input_file',
        type=Path,
        help='Input Alpha WDT file'
    )
    parser.add_argument(
        '-o', '--output-dir',
        type=Path,
        help='Output directory (default: input_dir/converted_YYYYMMDD_HHMMSS)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output'
    )
    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Validate input file
    if not args.input_file.exists():
        print(f"Error: Input file not found: {args.input_file}", file=sys.stderr)
        return 1

    if not args.input_file.is_file():
        print(f"Error: Input path is not a file: {args.input_file}", file=sys.stderr)
        return 1

    # Create output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = args.input_file.parent / f'converted_{timestamp}'

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Read input WDT
        revm, dhpm, niam = read_alpha_wdt(args.input_file)
        
        if args.debug:
            print(f"Input WDT: {args.input_file}")
            print(f"Version: {revm.version}")
            print(f"Flags: 0x{dhpm.flags:08x}")
            print(f"ADT cells: {sum(1 for row in niam.cells for cell in row if cell.offset > 0)}")

        # Convert WDT and ADTs
        convert_wdt(args.input_file, output_dir)
        print(f"Converted files saved to: {output_dir}")

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        if args.debug:
            raise
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
