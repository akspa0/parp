import os
import struct
import logging
import array
from datetime import datetime
from pathlib import Path
from chunk_definitions import (
    parse_mver, parse_mphd, parse_main, parse_mdnm, parse_monm, parse_mcnk,
    parse_mhdr, parse_mcin, parse_mtex, parse_mddf, parse_modf, parse_mwmo,
    parse_mwid, parse_mmdx, parse_mmid, text_based_visualization
)
from adt_parser.mcnk_decoders import MCNKHeader
from adt_parser.texture_decoders import TextureManager
from chunk_handler import WDTFile, ChunkRef
from wdt_db import (
    setup_database, insert_wdt_record, insert_map_tile, insert_texture,
    insert_m2_model, insert_wmo_model, insert_m2_placement, insert_wmo_placement,
    insert_tile_mcnk, insert_tile_layer, insert_chunk_offset, insert_adt_offsets,
    insert_height_map, insert_liquid_data
)

def write_visualization_to_file(grid):
    """Write text-based visualization of the ADT grid"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    vis_filename = f"adt_visualization_{timestamp}.txt"
    visualization = "\n".join(
        "".join("#" if cell == 1 else "." for cell in row)
        for row in grid
    )
    with open(vis_filename, 'w') as vis_file:
        vis_file.write("Text-based visualization of the ADT grid:\n")
        vis_file.write(visualization + "\n")
    print(f"Grid visualization saved to: {vis_filename}")

def analyze_wdt(filepath: str, db_path: str = "wdt_analysis.db") -> None:
    """
    Analyze WDT file using memory mapping and store results in database
    """
    # Setup logging with detailed output for header info
    log_filename = f"wdt_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        filename=log_filename,
        filemode='w',
        format='%(asctime)s [%(levelname)s] %(message)s',
        level=logging.INFO
    )

    # Also log to console for important messages
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    logging.info(f"\nAnalyzing WDT file: {filepath}")
    logging.info("=" * 50)
    
    # Setup database
    conn = setup_database(db_path)
    
    try:
        with WDTFile(Path(filepath)) as wdt:
            # First pass: Detect format and track chunk order
            print("\nPhase 1: Analyzing file structure...")
            chunk_order = []
            is_alpha = False
            version = None
            flags = None
            
            # Track all chunks and their offsets
            pos = 0
            while pos < len(wdt.mm):
                if pos + 8 > len(wdt.mm):
                    break
                    
                chunk_name_raw = wdt.mm[pos:pos+4]
                chunk_name = chunk_name_raw[::-1].decode('ascii', 'ignore') if wdt.reverse_names else chunk_name_raw.decode('ascii', 'ignore')
                chunk_size = struct.unpack('<I', wdt.mm[pos+4:pos+8])[0]
                
                chunk_order.append(chunk_name)
                
                # Check for Alpha format indicators
                if chunk_name in ['MDNM', 'MONM']:
                    is_alpha = True
                    print("Detected Alpha WDT format")
                    
                # Get version and flags
                if chunk_name == 'MVER':
                    version_info = parse_mver(wdt.mm[pos+8:pos+8+chunk_size])
                    version = version_info['version']
                    logging.info(f"WDT Version: {version}")
                elif chunk_name == 'MPHD':
                    header_info = parse_mphd(wdt.mm[pos+8:pos+8+chunk_size])
                    flags = header_info['flags']
                    flags_decoded = header_info['decoded_flags']
                    logging.info(f"Map Header Flags: {flags:#x}")
                    for flag_name, flag_value in flags_decoded.items():
                        if flag_value:
                            logging.info(f"  {flag_name}: {flag_value}")
                
                pos += 8 + chunk_size
            
            map_name = os.path.splitext(os.path.basename(filepath))[0]
            wdt_id = insert_wdt_record(
                conn, filepath, map_name, version, flags,
                bool(flags & 0x1),  # is_wmo_based
                ','.join(chunk_order),
                'alpha' if is_alpha else 'retail'
            )
            
            # Second pass: Process chunks and store offsets
            print("\nPhase 2: Processing chunks...")
            pos = 0
            while pos < len(wdt.mm):
                if pos + 8 > len(wdt.mm):
                    break
                    
                chunk_name_raw = wdt.mm[pos:pos+4]
                chunk_name = chunk_name_raw[::-1].decode('ascii', 'ignore') if wdt.reverse_names else chunk_name_raw.decode('ascii', 'ignore')
                chunk_size = struct.unpack('<I', wdt.mm[pos+4:pos+8])[0]
                
                insert_chunk_offset(conn, wdt_id, chunk_name, pos, chunk_size, pos + 8)
                pos += 8 + chunk_size
            
            # Third pass: Process map tiles and ADT data
            print("\nPhase 3: Processing map structure...")
            grid = [[0] * 64 for _ in range(64)]
            active_tiles = 0
            active_tiles_data = []  # Store tiles for batch processing
            
            for chunk_ref, data in wdt.get_chunks_by_type('MAIN'):
                main_info = parse_main(data, wdt)
                total_tiles = len(main_info['entries'])
                processed_tiles = 0
                
                for tile in main_info['entries']:
                    x, y = tile['coordinates']['x'], tile['coordinates']['y']
                    processed_tiles += 1
                    
                    if processed_tiles % 100 == 0:
                        print(f"Processing tile {processed_tiles}/{total_tiles}...")
                    
                    if tile['offset'] > 0:
                        grid[y][x] = 1
                        active_tiles += 1
                        
                        # Insert map tile record
                        tile_id = insert_map_tile(
                            conn, wdt_id, x, y,
                            tile['offset'], tile['size'],
                            tile['flags'], tile['async_id']
                        )
                        
                        # Process ADT data
                        try:
                            # Store ADT chunk offsets with format-specific handling
                            if is_alpha:
                                # Alpha format has simpler chunk structure
                                offsets = {
                                    'MHDR': 0,  # Not used in Alpha
                                    'MCIN': 0,  # Not used in Alpha
                                    'MTEX': tile['offset'],  # MTEX starts at tile offset
                                    'MMDX': 0,  # Not used in Alpha (uses MDNM instead)
                                    'MMID': 0,  # Not used in Alpha
                                    'MWMO': 0,  # Not used in Alpha (uses MONM instead)
                                    'MWID': 0,  # Not used in Alpha
                                    'MDDF': 0,  # Model placements handled differently in Alpha
                                    'MODF': 0   # Model placements handled differently in Alpha
                                }
                                
                                # Calculate MCNK offset (after MTEX)
                                if 'mcnk_data' in tile:
                                    mcnk_offset = tile['offset'] + 8  # Skip MTEX header
                                    offsets['MCNK'] = mcnk_offset
                                
                                logging.info(f"Alpha format offsets for tile ({x}, {y}): MTEX={offsets['MTEX']}, MCNK={offsets.get('MCNK', 0)}")
                            else:
                                # Retail format offsets
                                offsets = {
                                    'MHDR': 0,
                                    'MCIN': 0,
                                    'MTEX': 0,
                                    'MMDX': 0,
                                    'MMID': 0,
                                    'MWMO': 0,
                                    'MWID': 0,
                                    'MDDF': 0,
                                    'MODF': 0
                                }
                                
                                # Get offsets from MCNK data if available
                                if 'mcnk_data' in tile and 'offsets' in tile['mcnk_data']:
                                    mcnk_offsets = tile['mcnk_data']['offsets']
                                    for chunk_name, offset in mcnk_offsets.items():
                                        if chunk_name.upper() in offsets:
                                            offsets[chunk_name.upper()] = offset
                                
                                # Get additional offsets from tile data
                                if 'offsets' in tile:
                                    for chunk_name, offset in tile['offsets'].items():
                                        if chunk_name.upper() in offsets:
                                            offsets[chunk_name.upper()] = offset
                            
                            print(f"Found chunk offsets for tile ({x}, {y}): {[k for k, v in offsets.items() if v > 0]}")
                            insert_adt_offsets(conn, wdt_id, x, y, offsets)
                            
                            # Get texture information first
                            texture_info = {}
                            if is_alpha:
                                # For Alpha format, check MTEX chunks
                                for chunk_ref, mtex_data in wdt.get_chunks_by_type('MTEX'):
                                    mtex_info = parse_mtex(mtex_data)
                                    if 'textures' in mtex_info:
                                        for i, tex_path in enumerate(mtex_info['textures']):
                                            texture_info[i] = {
                                                'path': tex_path,
                                                'flags': {'has_alpha': False, 'is_terrain': True}
                                            }
                                            # Store texture info for batch insertion
                                            texture_info[i] = {
                                                'path': tex_path,
                                                'flags': {'has_alpha': False, 'is_terrain': True},
                                                'layer_index': i
                                            }
                                            
                                            if i % 100 == 0:  # Progress indicator for large texture sets
                                                print(f"Processed {i} textures for tile ({x}, {y})...")
                                    
                                    # Batch insert textures
                                    if texture_info:
                                        cursor = conn.cursor()
                                        cursor.executemany(
                                            '''INSERT INTO wdt_textures (
                                                wdt_id, tile_x, tile_y, texture_path,
                                                layer_index, blend_mode, has_alpha,
                                                is_compressed, effect_id, flags
                                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                            [(
                                                wdt_id, x, y,
                                                info['path'],
                                                info['layer_index'],
                                                0,  # blend_mode (not in Alpha)
                                                0,  # has_alpha (will be set by layer flags)
                                                0,  # is_compressed (not in Alpha)
                                                0,  # effect_id (not in Alpha)
                                                0   # flags (will be set by layer flags)
                                            ) for info in texture_info.values()]
                                        )
                                        conn.commit()
                                        print(f"Inserted {len(texture_info)} textures for tile ({x}, {y})")
                            
                            # Store tiles for batch processing
                            if 'mcnk_data' in tile:
                                tile['coordinates'] = {'x': x, 'y': y}
                                active_tiles_data.append(tile)
                        except Exception as e:
                            logging.error(f"Failed to process ADT data at ({x}, {y}): {e}")
            
            # Process collected tiles using multi-threaded processor
            if active_tiles_data:
                print(f"\nProcessing {len(active_tiles_data)} active tiles using multiple threads...")
                from mcnk_processor import process_wdt_tiles
                
                processing_stats = process_wdt_tiles(
                    wdt_file=wdt,
                    wdt_id=wdt_id,
                    tiles=active_tiles_data,
                    db_path=db_path,
                    is_alpha=is_alpha,
                    max_workers=4  # Adjust based on system capabilities
                )
                
                print(f"\nTile Processing Results:")
                print(f"Total Tiles: {processing_stats['total']}")
                print(f"Successfully Processed: {processing_stats['successful']}")
                print(f"Failed: {processing_stats['failed']}")
                if processing_stats['errors']:
                    print("\nErrors encountered:")
                    for error in processing_stats['errors'][:5]:  # Show first 5 errors
                        print(f"  - {error}")
                    if len(processing_stats['errors']) > 5:
                        print(f"  ... and {len(processing_stats['errors']) - 5} more errors")
            
            print(f"\nProcessed {active_tiles} active map tiles")
            
            # Fourth pass: Process models and textures
            print("\nPhase 4: Processing assets...")
            
            # Store model filenames first (with tile_x = -1, tile_y = -1)
            m2_model_ids = []  # Store IDs in order to match file's name_id order
            wmo_model_ids = []  # Store IDs in order to match file's name_id order
            
            if is_alpha:
                # Process M2 filenames (MDNM)
                for chunk_ref, data in wdt.get_chunks_by_type('MDNM'):
                    mdnm_info = parse_mdnm(data)
                    for model_path in mdnm_info['names']:
                        model_id = insert_m2_model(conn, wdt_id, -1, -1, model_path, 'alpha')
                        m2_model_ids.append(model_id)
                
                # Process WMO filenames (MONM)
                for chunk_ref, data in wdt.get_chunks_by_type('MONM'):
                    monm_info = parse_monm(data)
                    for model_path in monm_info['names']:
                        model_id = insert_wmo_model(conn, wdt_id, -1, -1, model_path, 'alpha')
                        wmo_model_ids.append(model_id)
            else:
                # Process M2 filenames (MMDX)
                for chunk_ref, data in wdt.get_chunks_by_type('MMDX'):
                    mmdx_info = parse_mmdx(data)
                    for model_path in mmdx_info['names']:
                        model_id = insert_m2_model(conn, wdt_id, -1, -1, model_path, 'retail')
                        m2_model_ids.append(model_id)
                
                # Process WMO filenames (MWMO)
                for chunk_ref, data in wdt.get_chunks_by_type('MWMO'):
                    mwmo_info = parse_mwmo(data)
                    for model_path in mwmo_info['names']:
                        model_id = insert_wmo_model(conn, wdt_id, -1, -1, model_path, 'retail')
                        wmo_model_ids.append(model_id)
            
            # Process model placements
            for chunk_ref, data in wdt.get_chunks_by_type('MDDF'):
                mddf_info = parse_mddf(data)
                for entry in mddf_info['entries']:
                    tile_x = int(entry['position']['x'] / 533.33333)
                    tile_y = int(entry['position']['y'] / 533.33333)
                    
                    # Get the model_id using the name_id as an index
                    if entry['name_id'] >= len(m2_model_ids):
                        logging.error(f"Invalid M2 name_id {entry['name_id']} (max: {len(m2_model_ids)-1})")
                        continue
                    
                    model_id = m2_model_ids[entry['name_id']]
                    insert_m2_placement(
                        conn, wdt_id, tile_x, tile_y, model_id,
                        entry['unique_id'],
                        (entry['position']['x'], entry['position']['y'], entry['position']['z']),
                        (entry['rotation']['x'], entry['rotation']['y'], entry['rotation']['z']),
                        entry['scale'],
                        entry['flags']
                    )
            
            # Process WMO placements
            print("\nProcessing WMO models...")
            for chunk_ref, data in wdt.get_chunks_by_type('MODF'):
                try:
                    modf_info = parse_modf(data)
                    for entry in modf_info['entries']:
                        try:
                            # Calculate tile coordinates
                            tile_x = int(entry['position']['x'] / 533.33333)
                            tile_y = int(entry['position']['y'] / 533.33333)
                            
                            # Get the model_id using the name_id as an index
                            if entry['name_id'] >= len(wmo_model_ids):
                                logging.error(f"Invalid WMO name_id {entry['name_id']} (max: {len(wmo_model_ids)-1})")
                                continue
                            
                            model_id = wmo_model_ids[entry['name_id']]
                            
                            # Extract position and rotation
                            position = (
                                float(entry['position']['x']),
                                float(entry['position']['y']),
                                float(entry['position']['z'])
                            )
                            rotation = (
                                float(entry['rotation']['x']),
                                float(entry['rotation']['y']),
                                float(entry['rotation']['z'])
                            )
                            
                            # Handle bounds properly
                            bounds = entry.get('bounds', {})
                            if bounds:
                                bounds_min = bounds.get('min', {})
                                bounds_max = bounds.get('max', {})
                                bounds_min_tuple = (
                                    float(bounds_min.get('x', 0)),
                                    float(bounds_min.get('y', 0)),
                                    float(bounds_min.get('z', 0))
                                )
                                bounds_max_tuple = (
                                    float(bounds_max.get('x', 0)),
                                    float(bounds_max.get('y', 0)),
                                    float(bounds_max.get('z', 0))
                                )
                            else:
                                bounds_min_tuple = (0.0, 0.0, 0.0)
                                bounds_max_tuple = (0.0, 0.0, 0.0)
                            
                            insert_wmo_placement(
                                conn, wdt_id, tile_x, tile_y, model_id,
                                entry['unique_id'],
                                position, rotation,
                                float(entry['scale']),
                                entry['flags'],
                                int(entry.get('doodad_set', 0)),
                                int(entry.get('name_set', 0)),
                                bounds_min_tuple,
                                bounds_max_tuple
                            )
                            
                        except Exception as e:
                            logging.error(f"Error processing WMO placement: {e}")
                            continue
                            
                except Exception as e:
                    logging.error(f"Error processing MODF chunk: {e}")
                    continue
            
            print(f"Format: {'Alpha' if is_alpha else 'Retail'} WDT")
            print(f"Database: {db_path}")
            print(f"Errors logged to: {log_filename}")
            
            # Write visualization to file
            write_visualization_to_file(grid)
            
    except Exception as e:
        logging.error(f"Error analyzing WDT file: {e}")
        print(f"\nError: {e}")
        print(f"Check {log_filename} for details")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python analyze_wdt.py <path_to_wdt_file> [database_path]")
        sys.exit(1)

    filepath = sys.argv[1]
    db_path = sys.argv[2] if len(sys.argv) > 2 else "wdt_analysis.db"

    if not os.path.isfile(filepath):
        print(f"Error: File {filepath} not found.")
        sys.exit(1)

    analyze_wdt(filepath, db_path)
