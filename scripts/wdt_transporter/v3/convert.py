"""Convert Alpha WDT files to WotLK format."""
import argparse
from datetime import datetime
from pathlib import Path
import struct
from typing import BinaryIO, List, Optional, Tuple
import sys

from chunks.base import Chunk
from chunks import (
    AlphaRevmChunk, AlphaMphdChunk, AlphaNiamChunk, AlphaAdt,
    AlphaMdnmChunk, AlphaMonmChunk,
    WotlkRevmChunk, WotlkMphdChunk, WotlkNiamChunk, WotlkAdt, WotlkAdtCell
)

def read_alpha_wdt(path: Path) -> Tuple[AlphaRevmChunk, AlphaMphdChunk, AlphaNiamChunk, AlphaMdnmChunk, AlphaMonmChunk, Optional[Chunk]]:
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

    # Parse required chunks
    revm = AlphaRevmChunk.from_chunk(chunks['REVM'])
    mphd = AlphaMphdChunk.from_chunk(chunks['DHPM'])
    niam = AlphaNiamChunk.from_chunk(chunks['NIAM'])

    # Parse optional chunks (with empty defaults)
    mdnm = AlphaMdnmChunk.from_chunk(chunks['MNMD']) if 'MNMD' in chunks else AlphaMdnmChunk(filenames=[])
    monm = AlphaMonmChunk.from_chunk(chunks['MNOM']) if 'MNOM' in chunks else AlphaMonmChunk(filenames=[])
    modf = chunks.get('FDOM')  # Get MODF chunk if it exists

    return revm, mphd, niam, mdnm, monm, modf


def write_string_chunk(f: BinaryIO, letters: str, strings: List[str]) -> None:
    """Write chunk containing null-terminated strings.
    
    The strings are concatenated with null bytes between them,
    and a final null byte at the end.
    """
    # Convert strings to bytes and join with null bytes
    data = b'\0'.join(s.encode('ascii') for s in strings)
    if data:  # Add final null byte if we have data
        data += b'\0'
    
    chunk = Chunk(letters=letters, size=len(data), data=data)
    chunk.write(f)


def write_indices_chunk(f: BinaryIO, letters: str, count: int) -> None:
    """Write chunk containing sequential indices.
    
    Creates a chunk with indices from 0 to count-1 as 32-bit integers.
    """
    if count == 0:
        # Write empty chunk if no indices
        data = struct.pack('<I', 0)
    else:
        # Pack indices as 32-bit integers
        data = b''.join(struct.pack('<I', i) for i in range(count))
    
    chunk = Chunk(letters=letters, size=len(data), data=data)
    chunk.write(f)


def write_wotlk_wdt(path: Path, revm: WotlkRevmChunk, mphd: WotlkMphdChunk, niam: WotlkNiamChunk,
                   mdnm: AlphaMdnmChunk, monm: AlphaMonmChunk, modf: Optional[Chunk] = None) -> None:
    """Write WotLK WDT file."""
    with open(path, 'wb') as f:
        # Write required chunks
        revm.to_chunk().write(f)
        mphd.to_chunk().write(f)
        niam.to_chunk().write(f)

        # Write model chunks
        write_string_chunk(f, 'XDMM', mdnm.filenames)  # MMDX
        write_indices_chunk(f, 'DIMM', len(mdnm.filenames))  # MMID

        # Write WMO chunks - only use WMO names if WMO-based
        if mphd.is_wmo_based():
            write_string_chunk(f, 'OMWM', monm.filenames)  # MWMO
            write_indices_chunk(f, 'DIWM', len(monm.filenames))  # MWID
            # Write MODF chunk if WMO-based
            if modf:
                modf.write(f)
        else:
            # Write empty WMO chunks
            data = struct.pack('<I', 0)  # 4 bytes of zeros
            Chunk(letters='OMWM', size=4, data=data).write(f)  # MWMO
            Chunk(letters='DIWM', size=4, data=data).write(f)  # MWID

        # Write empty MH2O chunk (required by noggit-red)
        data = bytearray(8)  # 8 bytes of zeros
        Chunk(letters='O2HM', size=8, data=bytes(data)).write(f)


def convert_wdt(input_path: Path, output_dir: Path) -> None:
    """Convert Alpha WDT to WotLK format."""
    # Read alpha WDT
    alpha_revm, alpha_mphd, alpha_niam, alpha_mdnm, alpha_monm, alpha_modf = read_alpha_wdt(input_path)

    # Convert to WotLK format
    wotlk_revm = WotlkRevmChunk(version=18)  # Always 18 in WotLK
    wotlk_mphd = WotlkMphdChunk.from_alpha(alpha_mphd)

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
    write_wotlk_wdt(output_path, wotlk_revm, wotlk_mphd, wotlk_niam, alpha_mdnm, alpha_monm, alpha_modf)

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

        # Convert to WotLK format using model/WMO names from WDT
        wotlk_adt = WotlkAdt.from_alpha_adt(alpha_adt, alpha_mdnm.filenames, alpha_monm.filenames)

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
        revm, mphd, niam, mdnm, monm, modf = read_alpha_wdt(args.input_file)
        
        if args.debug:
            print(f"Input WDT: {args.input_file}")
            print(f"Version: {revm.version}")
            print(f"WMO-based: {mphd.is_wmo_based()}")
            print(f"ADT cells: {sum(1 for row in niam.cells for cell in row if cell.offset > 0)}")
            print(f"Models: {len(mdnm.filenames)}")
            print(f"WMOs: {len(monm.filenames)}")
            print(f"Has MODF: {modf is not None}")

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
