import struct
import argparse
import os
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import BinaryIO
from pathlib import Path

@dataclass
class Offsets:
    """A class that contains offsets"""
    x: int
    y: int
    xf: float
    zf: float
    z_off: float
    wdt_x_off: float
    wdt_y_off: float
    wdt_z_off: float

@dataclass
class MCIN:
    """MCIN structure for file offsets and sizes"""
    offset: int
    size: int
    temp1: int
    temp2: int

class OffsetFixData:
    """Main data structure for offset fixing operations"""
    def __init__(self):
        self.offset = Offsets(0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        self.offset_mddf: int = 0
        self.offset_modf: int = 0
        self.positions_mcnk: list[int] = [0] * 256
        self.positions: list[MCIN] = []

def setup_logging(output_dir: Path) -> None:
    """Set up logging with timestamp in filename"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = output_dir / f"offset_fix_{timestamp}.log"
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Setup file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    
    # Setup console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Setup logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

def find_mcnks(zone_file: BinaryIO, off_data: OffsetFixData) -> None:
    """Find and read MCNK chunks from the zone file"""
    zone_file.seek(92)
    for _ in range(256):
        data = zone_file.read(16)  # MCIN struct is 4 ints = 16 bytes
        offset, size, temp1, temp2 = struct.unpack('IIII', data)
        off_data.positions.append(MCIN(offset, size, temp1, temp2))

def find_mddf_and_modf(zone_file: BinaryIO, off_data: OffsetFixData) -> None:
    """Find MDDF and MODF offsets in the zone file"""
    zone_file.seek(0x30)
    off_data.offset_mddf = struct.unpack('I', zone_file.read(4))[0]
    off_data.offset_modf = struct.unpack('I', zone_file.read(4))[0]

def fix_mcnks(zone_file: BinaryIO, off_data: OffsetFixData) -> None:
    """Fix MCNK chunk positions"""
    # Read initial position
    zone_file.seek(off_data.positions[0].offset + 0x68 + 8)
    old_y = struct.unpack('f', zone_file.read(4))[0]
    old_x = struct.unpack('f', zone_file.read(4))[0]

    # Calculate base offsets
    y = (1600.0 * (32 - off_data.offset.y)) / 3.0
    x = (1600.0 * (32 - off_data.offset.x)) / 3.0

    off_data.offset.xf = old_x - x
    off_data.offset.zf = old_y - y

    # Process all chunks
    for i in range(256):
        # Read MCNK position
        zone_file.seek(off_data.positions[i].offset + 0x60 + 8)
        off_data.positions_mcnk[i] = struct.unpack('I', zone_file.read(4))[0]
        off_data.positions_mcnk[i] += off_data.positions[i].offset

        # Calculate and write Y coordinate
        y = (1600.0 * (32 - off_data.offset.y)) / 3.0 - 100.0 * (i // 16) / 3.0
        zone_file.seek(off_data.positions[i].offset + 0x68 + 8)
        zone_file.write(struct.pack('f', y))

        # Calculate and write X coordinate
        x = (1600.0 * (32 - off_data.offset.x)) / 3.0 - 100.0 * (i % 16) / 3.0
        zone_file.seek(off_data.positions[i].offset + 0x68 + 12)
        zone_file.write(struct.pack('f', x))

        # Adjust Z coordinate
        zone_file.seek(off_data.positions[i].offset + 0x68 + 16)
        y = struct.unpack('f', zone_file.read(4))[0]
        y += off_data.offset.z_off
        zone_file.seek(off_data.positions[i].offset + 0x68 + 16)
        zone_file.write(struct.pack('f', y))

def fix_doodads(zone_file: BinaryIO, off_data: OffsetFixData) -> None:
    """Fix doodad positions"""
    zone_file.seek(0x14 + 0x04 + off_data.offset_mddf)
    num_doodads = struct.unpack('I', zone_file.read(4))[0] // 36

    zone_file.seek(8, 1)  # Skip 8 bytes
    for _ in range(num_doodads):
        # Read coordinates
        coords = list(struct.unpack('fff', zone_file.read(12)))
        coords[0] += off_data.offset.xf
        coords[2] += off_data.offset.zf

        # Write back adjusted coordinates
        zone_file.seek(-12, 1)
        zone_file.write(struct.pack('fff', *coords))
        zone_file.seek(24, 1)

def fix_wmos(zone_file: BinaryIO, off_data: OffsetFixData) -> None:
    """Fix WMO (World Map Object) positions"""
    zone_file.seek(0x14 + 0x04 + off_data.offset_modf)
    num_wmos = struct.unpack('I', zone_file.read(4))[0] // 64

    base_pos = 0x14 + 0x04 + off_data.offset_modf + 0x08 + 4
    for i in range(num_wmos):
        # Process three sets of coordinates for each WMO
        for offset in [0, 24, 36]:
            pos = base_pos + i * 64 + offset
            zone_file.seek(pos)
            coords = list(struct.unpack('fff', zone_file.read(12)))
            
            # Adjust coordinates
            coords[0] += off_data.offset.xf + off_data.offset.wdt_x_off
            coords[1] += off_data.offset.z_off + off_data.offset.wdt_z_off
            coords[2] += off_data.offset.zf + off_data.offset.wdt_y_off
            
            # Write back adjusted coordinates
            zone_file.seek(pos)
            zone_file.write(struct.pack('fff', *coords))

def process_zone_file(input_path: Path, output_path: Path, offset_data: OffsetFixData) -> None:
    """Process a zone file with the given offset data"""
    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Copy input file to output location
    with open(input_path, 'rb') as src, open(output_path, 'wb') as dst:
        dst.write(src.read())
    
    # Process the copied file
    logging.info(f"Processing file: {input_path.name}")
    try:
        with open(output_path, 'rb+') as zone_file:
            find_mcnks(zone_file, offset_data)
            find_mddf_and_modf(zone_file, offset_data)
            fix_mcnks(zone_file, offset_data)
            fix_doodads(zone_file, offset_data)
            fix_wmos(zone_file, offset_data)
        logging.info(f"Successfully processed: {input_path.name}")
    except Exception as e:
        logging.error(f"Error processing {input_path.name}: {str(e)}")
        raise

def process_directory(input_dir: Path, output_dir: Path, offset_data: OffsetFixData) -> None:
    """Process all .adt files in the input directory"""
    # Ensure directories exist
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Set up logging
    setup_logging(output_dir)
    
    logging.info(f"Starting to process files from: {input_dir}")
    logging.info(f"Output directory: {output_dir}")
    
    # Process all .adt files
    adt_files = list(input_dir.glob("*.adt"))
    if not adt_files:
        logging.warning(f"No .adt files found in {input_dir}")
        return
    
    logging.info(f"Found {len(adt_files)} .adt files to process")
    
    for adt_file in adt_files:
        output_path = output_dir / adt_file.name
        try:
            process_zone_file(adt_file, output_path, offset_data)
        except Exception as e:
            logging.error(f"Failed to process {adt_file.name}: {str(e)}")
            continue

def main():
    parser = argparse.ArgumentParser(description="Process ADT files with offset fixes")
    parser.add_argument("input_dir", help="Input directory containing .adt files")
    parser.add_argument("output_dir", help="Output directory for processed files")
    parser.add_argument("--x-offset", type=int, default=0, help="X offset value")
    parser.add_argument("--y-offset", type=int, default=0, help="Y offset value")
    parser.add_argument("--z-offset", type=float, default=0.0, help="Z offset value")
    parser.add_argument("--wdt-x-offset", type=float, default=0.0, help="WDT X offset value")
    parser.add_argument("--wdt-y-offset", type=float, default=0.0, help="WDT Y offset value")
    parser.add_argument("--wdt-z-offset", type=float, default=0.0, help="WDT Z offset value")
    
    args = parser.parse_args()
    
    # Create offset data with command line arguments
    offset_data = OffsetFixData()
    offset_data.offset = Offsets(
        x=args.x_offset,
        y=args.y_offset,
        xf=0.0,  # Will be calculated during processing
        zf=0.0,  # Will be calculated during processing
        z_off=args.z_offset,
        wdt_x_off=args.wdt_x_offset,
        wdt_y_off=args.wdt_y_offset,
        wdt_z_off=args.wdt_z_offset
    )
    
    # Process the directory
    process_directory(
        Path(args.input_dir),
        Path(args.output_dir),
        offset_data
    )

if __name__ == "__main__":
    main()
