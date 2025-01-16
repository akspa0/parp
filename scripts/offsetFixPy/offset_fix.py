import argparse
import logging
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from construct import Struct, Int32ul, Float32l, Array, Seek, Tell, this

# Binary structures using construct
MCIN = Struct(
    "offset" / Int32ul,
    "size" / Int32ul,
    "temp1" / Int32ul,
    "temp2" / Int32ul
)

MCIN_Array = Struct(
    Seek(92),
    "entries" / Array(256, MCIN)
)

Offsets_Header = Struct(
    Seek(0x30),
    "mddf_offset" / Int32ul,
    "modf_offset" / Int32ul
)

Coords = Struct(
    "x" / Float32l,
    "y" / Float32l,
    "z" / Float32l
)

MDDF_Header = Struct(
    "size" / Int32ul,
    Seek(8, 1),  # relative seek
)

MODF_Header = Struct(
    "size" / Int32ul,
    Seek(8, 1),  # relative seek
)

@dataclass
class Offsets:
    """Class that contains offsets"""
    x: int
    y: int
    xf: float = 0.0
    zf: float = 0.0
    z_off: float = 0.0
    wdt_x_off: float = 0.0
    wdt_y_off: float = 0.0
    wdt_z_off: float = 0.0

class OffsetFixData:
    """Main data structure for offset fixing operations"""
    def __init__(self):
        self.offset = Offsets(0, 0)
        self.offset_mddf: int = 0
        self.offset_modf: int = 0
        self.positions_mcnk: list[int] = [0] * 256
        self.positions: list[dict] = []

def setup_logging(output_dir: Path) -> None:
    """Set up logging with timestamp in filename"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = output_dir / f"offset_fix_{timestamp}.log"
    
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

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
            # Read MCIN array
            mcin_data = MCIN_Array.parse_stream(zone_file)
            offset_data.positions = mcin_data.entries
            
            # Read offsets
            offsets = Offsets_Header.parse_stream(zone_file)
            offset_data.offset_mddf = offsets.mddf_offset
            offset_data.offset_modf = offsets.modf_offset
            
            # Fix MCNK chunks
            zone_file.seek(offset_data.positions[0].offset + 0x68 + 8)
            old_coords = Coords.parse_stream(zone_file)
            
            # Calculate base offsets
            y = (1600.0 * (32 - offset_data.offset.y)) / 3.0
            x = (1600.0 * (32 - offset_data.offset.x)) / 3.0
            
            offset_data.offset.xf = old_coords.x - x
            offset_data.offset.zf = old_coords.y - y
            
            # Process all chunks
            for i in range(256):
                zone_file.seek(offset_data.positions[i].offset + 0x60 + 8)
                offset_data.positions_mcnk[i] = Int32ul.parse_stream(zone_file)
                offset_data.positions_mcnk[i] += offset_data.positions[i].offset
                
                # Calculate and write coordinates
                y = (1600.0 * (32 - offset_data.offset.y)) / 3.0 - 100.0 * (i // 16) / 3.0
                x = (1600.0 * (32 - offset_data.offset.x)) / 3.0 - 100.0 * (i % 16) / 3.0
                
                zone_file.seek(offset_data.positions[i].offset + 0x68 + 8)
                Coords.build_stream(dict(x=x, y=y, z=0), zone_file)
                
                # Adjust Z coordinate
                zone_file.seek(offset_data.positions[i].offset + 0x68 + 16)
                z = Float32l.parse_stream(zone_file)
                z += offset_data.offset.z_off
                zone_file.seek(offset_data.positions[i].offset + 0x68 + 16)
                Float32l.build_stream(z, zone_file)
            
            # Fix doodads
            zone_file.seek(0x14 + 0x04 + offset_data.offset_mddf)
            mddf_header = MDDF_Header.parse_stream(zone_file)
            num_doodads = mddf_header.size // 36
            
            for _ in range(num_doodads):
                coords = Coords.parse_stream(zone_file)
                coords.x += offset_data.offset.xf
                coords.z += offset_data.offset.zf
                
                zone_file.seek(-12, 1)
                Coords.build_stream(coords, zone_file)
                zone_file.seek(24, 1)
            
            # Fix WMOs
            zone_file.seek(0x14 + 0x04 + offset_data.offset_modf)
            modf_header = MODF_Header.parse_stream(zone_file)
            num_wmos = modf_header.size // 64
            
            base_pos = 0x14 + 0x04 + offset_data.offset_modf + 0x08 + 4
            for i in range(num_wmos):
                for offset in [0, 24, 36]:
                    pos = base_pos + i * 64 + offset
                    zone_file.seek(pos)
                    coords = Coords.parse_stream(zone_file)
                    
                    coords.x += offset_data.offset.xf + offset_data.offset.wdt_x_off
                    coords.y += offset_data.offset.z_off + offset_data.offset.wdt_z_off
                    coords.z += offset_data.offset.zf + offset_data.offset.wdt_y_off
                    
                    zone_file.seek(pos)
                    Coords.build_stream(coords, zone_file)
            
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
