import os
import json
import struct
import logging
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Set, Tuple
from chunk_definitions import (
    parse_mver, parse_mphd, parse_main, parse_mdnm, parse_monm,
    parse_mhdr, parse_mcin, parse_mtex, parse_mddf, parse_modf, parse_mwmo,
    parse_mwid, parse_mmdx, parse_mmid
)
from chunk_handler import WDTFile

@dataclass
class TileDefinition:
    x: int
    y: int
    offset: int
    size: int
    flags: int
    async_id: int
    chunks: Dict[str, Tuple[int, int]] = None  # chunk_name -> (offset, size)

    def __post_init__(self):
        self.chunks = {}

def create_output_dir(base_name: str) -> str:
    """Create timestamped output directory"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"output_{base_name}_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def write_visualization_to_file(grid, output_dir: str):
    """Write text-based visualization of the ADT grid"""
    vis_filename = os.path.join(output_dir, "adt_visualization.txt")
    visualization = "\n".join(
        "".join("#" if cell == 1 else "." for cell in row)
        for row in grid
    )
    with open(vis_filename, 'w') as vis_file:
        vis_file.write("Text-based visualization of the ADT grid:\n")
        vis_file.write(visualization + "\n")
    print(f"Grid visualization saved to: {vis_filename}")

def process_wdt_header(wdt: WDTFile, output_dir: str, base_name: str) -> dict:
    """Process and store WDT header data"""
    header_data = {
        'filename': wdt.path.name,
        'map_name': base_name,
        'version': None,
        'flags': None,
        'chunks': {},
        'models': {
            'm2': [],
            'wmo': []
        },
        'model_indices': {
            'm2': [],
            'wmo': []
        },
        'placements': {
            'm2': [],
            'wmo': []
        }
    }
    
    # Process MVER chunk
    for chunk_ref, data in wdt.get_chunks_by_type('MVER'):
        version_info = parse_mver(data)
        header_data['version'] = version_info['version']
    
    # Process MPHD chunk
    for chunk_ref, data in wdt.get_chunks_by_type('MPHD'):
        header_info = parse_mphd(data)
        header_data['flags'] = header_info
    
    # Process M2 model data
    m2_models = []
    for chunk_ref, data in wdt.get_chunks_by_type('MMDX'):
        mmdx_info = parse_mmdx(data)
        m2_models.extend(mmdx_info['names'])
    header_data['models']['m2'] = m2_models
    
    for chunk_ref, data in wdt.get_chunks_by_type('MMID'):
        mmid_info = parse_mmid(data)
        header_data['model_indices']['m2'] = mmid_info['indices']
    
    # Process WMO model data
    wmo_models = []
    for chunk_ref, data in wdt.get_chunks_by_type('MWMO'):
        mwmo_info = parse_mwmo(data)
        wmo_models.extend(mwmo_info['names'])
    header_data['models']['wmo'] = wmo_models
    
    for chunk_ref, data in wdt.get_chunks_by_type('MWID'):
        mwid_info = parse_mwid(data)
        header_data['model_indices']['wmo'] = mwid_info['indices']
    
    # Process M2 placement data
    for chunk_ref, data in wdt.get_chunks_by_type('MDDF'):
        mddf_info = parse_mddf(data)
        for entry in mddf_info['entries']:
            # Add model name to placement data
            model_id = entry['name_id']
            if 0 <= model_id < len(m2_models):
                entry['model_name'] = m2_models[model_id]
            header_data['placements']['m2'].append(entry)
    
    # Process WMO placement data
    for chunk_ref, data in wdt.get_chunks_by_type('MODF'):
        modf_info = parse_modf(data)
        for entry in modf_info['entries']:
            # Add model name to placement data
            model_id = entry['name_id']
            if 0 <= model_id < len(wmo_models):
                entry['model_name'] = wmo_models[model_id]
            header_data['placements']['wmo'].append(entry)
    
    # Store chunk order and offsets
    pos = 0
    while pos < len(wdt.mm):
        if pos + 8 > len(wdt.mm):
            break
            
        chunk_name_raw = wdt.mm[pos:pos+4]
        chunk_name = chunk_name_raw[::-1].decode('ascii', 'ignore') if wdt.reverse_names else chunk_name_raw.decode('ascii', 'ignore')
        chunk_size = struct.unpack('<I', wdt.mm[pos+4:pos+8])[0]
        
        header_data['chunks'][chunk_name] = {
            'offset': pos,
            'size': chunk_size,
            'data_offset': pos + 8
        }
        pos += 8 + chunk_size
    
    # Write header data to JSON
    header_file = os.path.join(output_dir, f"{base_name}_header.json")
    with open(header_file, 'w') as f:
        json.dump(header_data, f, indent=2)
    
    return header_data

def scan_tile_definitions(wdt: WDTFile) -> Dict[Tuple[int, int], TileDefinition]:
    """First pass: Scan file for all tile definitions"""
    tiles = {}
    grid = [[0] * 64 for _ in range(64)]
    
    for chunk_ref, data in wdt.get_chunks_by_type('MAIN'):
        main_info = parse_main(data)
        for entry in main_info['entries']:
            x, y = entry['coordinates']['x'], entry['coordinates']['y']
            if entry['offset'] > 0:
                grid[y][x] = 1
                tiles[(x, y)] = TileDefinition(
                    x=x,
                    y=y,
                    offset=entry['offset'],
                    size=entry['size'],
                    flags=entry['flags'],
                    async_id=entry['async_id']
                )
    
    return tiles, grid

def analyze_tile_chunks(wdt: WDTFile, tile: TileDefinition):
    """Second pass: Analyze what chunks this tile contains"""
    pos = tile.offset
    end_pos = pos + tile.size
    
    while pos < end_pos:
        if pos + 8 > len(wdt.mm):
            break
            
        chunk_name_raw = wdt.mm[pos:pos+4]
        chunk_name = chunk_name_raw[::-1].decode('ascii', 'ignore') if wdt.reverse_names else chunk_name_raw.decode('ascii', 'ignore')
        chunk_size = struct.unpack('<I', wdt.mm[pos+4:pos+8])[0]
        
        tile.chunks[chunk_name] = (pos + 8, chunk_size)  # Store data offset and size
        pos += 8 + chunk_size

def process_tile(wdt: WDTFile, tile: TileDefinition, output_dir: str, base_name: str):
    """Third pass: Process a single tile's data"""
    tile_data = {
        'info': asdict(tile),
        'chunks': {},
        'textures': [],
        'models': {
            'm2': [],
            'wmo': []
        },
        'model_indices': {
            'm2': [],
            'wmo': []
        },
        'placements': {
            'm2': [],
            'wmo': []
        },
        'mcnk': []
    }
    
    # Process each chunk
    for chunk_name, (offset, size) in tile.chunks.items():
        chunk_data = wdt.mm[offset:offset + size]
        tile_data['chunks'][chunk_name] = {
            'offset': offset,
            'size': size,
            'data_hex': chunk_data.hex()  # Store raw data as hex for debugging
        }
        
        # Process chunk data based on type
        if chunk_name == 'MTEX':
            mtex_info = parse_mtex(chunk_data)
            tile_data['textures'].extend(mtex_info['textures'])
        
        elif chunk_name == 'MMDX':
            mmdx_info = parse_mmdx(chunk_data)
            tile_data['models']['m2'].extend(mmdx_info['names'])
        
        elif chunk_name == 'MMID':
            mmid_info = parse_mmid(chunk_data)
            tile_data['model_indices']['m2'].extend(mmid_info['indices'])
        
        elif chunk_name == 'MWMO':
            mwmo_info = parse_mwmo(chunk_data)
            tile_data['models']['wmo'].extend(mwmo_info['names'])
        
        elif chunk_name == 'MWID':
            mwid_info = parse_mwid(chunk_data)
            tile_data['model_indices']['wmo'].extend(mwid_info['indices'])
        
        elif chunk_name == 'MDDF':
            mddf_info = parse_mddf(chunk_data)
            for entry in mddf_info['entries']:
                # Add model name to placement data
                model_id = entry['name_id']
                if 0 <= model_id < len(tile_data['models']['m2']):
                    entry['model_name'] = tile_data['models']['m2'][model_id]
                tile_data['placements']['m2'].append(entry)
        
        elif chunk_name == 'MODF':
            modf_info = parse_modf(chunk_data)
            for entry in modf_info['entries']:
                # Add model name to placement data
                model_id = entry['name_id']
                if 0 <= model_id < len(tile_data['models']['wmo']):
                    entry['model_name'] = tile_data['models']['wmo'][model_id]
                tile_data['placements']['wmo'].append(entry)
        
        elif chunk_name == 'MCNK':
            mcnk_info = parse_mcnk(chunk_data)
            tile_data['mcnk'].append(mcnk_info)
    
    # Write tile data to JSON
    tile_file = os.path.join(output_dir, f"{base_name}_{tile.x:02d}_{tile.y:02d}.json")
    with open(tile_file, 'w') as f:
        json.dump(tile_data, f, indent=2)

def analyze_wdt(filepath: str) -> None:
    """Analyze WDT file using a tile-centric approach"""
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    output_dir = create_output_dir(base_name)
    
    log_filename = os.path.join(output_dir, "wdt_analysis.log")
    logging.basicConfig(
        filename=log_filename,
        filemode='w',
        format='%(asctime)s [%(levelname)s] %(message)s',
        level=logging.ERROR
    )

    print(f"\nAnalyzing WDT file: {filepath}")
    print(f"Output directory: {output_dir}")
    print("=" * 50)
    
    try:
        with WDTFile(Path(filepath)) as wdt:
            # Process WDT header data
            print("\nPhase 1: Processing WDT header...")
            header_data = process_wdt_header(wdt, output_dir, base_name)
            
            # First pass: Get all tile definitions
            print("\nPhase 2: Scanning tile definitions...")
            tiles, grid = scan_tile_definitions(wdt)
            print(f"Found {len(tiles)} active tiles")
            write_visualization_to_file(grid, output_dir)
            
            # Second pass: Analyze chunks for each tile
            print("\nPhase 3: Analyzing tile chunks...")
            for coords, tile in tiles.items():
                analyze_tile_chunks(wdt, tile)
                print(f"Tile ({tile.x}, {tile.y}): {len(tile.chunks)} chunks")
            
            # Third pass: Process each tile
            print("\nPhase 4: Processing tiles...")
            for coords, tile in tiles.items():
                print(f"\nProcessing tile ({tile.x}, {tile.y})")
                process_tile(wdt, tile, output_dir, base_name)
            
            print("\nAnalysis Complete!")
            print("=" * 50)
            print(f"Output directory: {output_dir}")
            print(f"WDT header: {base_name}_header.json")
            print(f"Processed {len(tiles)} tile files")
            
            if os.path.exists(log_filename) and os.path.getsize(log_filename) > 0:
                print(f"Errors logged to: {log_filename}")
            
    except Exception as e:
        logging.error(f"Error analyzing WDT file: {e}")
        print(f"\nError: {e}")
        print(f"Check {log_filename} for details")
        raise

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python analyze_wdt.py <path_to_wdt_file>")
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.isfile(filepath):
        print(f"Error: File {filepath} not found.")
        sys.exit(1)

    analyze_wdt(filepath)
