import os
import struct
import logging
from datetime import datetime
from pathlib import Path
from chunk_definitions import (
    parse_mver, parse_mphd, parse_main, parse_mdnm, parse_monm, parse_mcnk,
    parse_mhdr, parse_mcin, parse_mtex, parse_mddf, parse_modf, parse_mwmo,
    parse_mwid, parse_mmdx, parse_mmid, text_based_visualization
)
from chunk_handler import WDTFile
from wdt_db import (
    setup_database, insert_wdt_record, insert_map_tile, insert_texture,
    insert_m2_model, insert_wmo_model, insert_m2_placement, insert_wmo_placement,
    insert_tile_mcnk, insert_tile_layer, insert_chunk_offset, insert_adt_offsets
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
            
            for chunk_ref, data in wdt.get_chunks_by_type('MAIN'):
                main_info = parse_main(data)
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
                            # Store ADT chunk offsets
                            if 'offsets' in tile:
                                print(f"Found chunk offsets for tile ({x}, {y}): {list(tile['offsets'].keys())}")
                                insert_adt_offsets(conn, wdt_id, x, y, tile['offsets'])
                            
                            # Process MCNK data
                            if 'mcnk_data' in tile:
                                print(f"Processing MCNK data for tile ({x}, {y})")
                                mcnk_id = insert_tile_mcnk(conn, wdt_id, x, y, tile['mcnk_data'])
                                
                                # Process layers
                                if 'layers' in tile['mcnk_data']:
                                    layer_count = len(tile['mcnk_data']['layers'])
                                    print(f"Found {layer_count} layers for tile ({x}, {y})")
                                    for i, layer in enumerate(tile['mcnk_data']['layers']):
                                        insert_tile_layer(conn, mcnk_id, i, layer['texture_id'], layer['flags'], layer['effect_id'])
                            
                            # Process textures
                            if 'textures' in tile:
                                texture_count = len(tile['textures'])
                                print(f"Found {texture_count} textures for tile ({x}, {y})")
                                for i, texture_info in enumerate(tile['textures']):
                                    if 'path' not in texture_info:
                                        logging.error(f"Missing path in texture info for tile ({x}, {y}): {texture_info}")
                                        continue
                                    insert_texture(conn, wdt_id, x, y,
                                               texture_info['path'],
                                               texture_info.get('layer_index', 0))
                                    
                        except Exception as e:
                            logging.error(f"Failed to process ADT data at ({x}, {y}): {e}")
            
            print(f"Found {active_tiles} active map tiles")
            
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
            m2_count = 0
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
                    m2_count += 1
            
            if m2_count > 0:
                print(f"Processed {m2_count} M2 model placements")
            
            # Process WMO placements
            wmo_count = 0
            print("\nProcessing WMO models...")
            for chunk_ref, data in wdt.get_chunks_by_type('MODF'):
                try:
                    modf_info = parse_modf(data)
                    total_entries = len(modf_info['entries'])
                    
                    for i, entry in enumerate(modf_info['entries'], 1):
                        if i % 100 == 0:
                            print(f"Processing WMO model {i}/{total_entries}...", end='\r')
                            
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
                            wmo_count += 1
                            
                        except Exception as e:
                            logging.error(f"Error processing WMO placement {i}: {e}")
                            continue
                            
                except Exception as e:
                    logging.error(f"Error processing MODF chunk: {e}")
                    continue
            
            if wmo_count > 0:
                print(f"Processed {wmo_count} WMO model placements")
            
            write_visualization_to_file(grid)
            
            # Gather statistics
            print("\nGathering statistics...")
            cursor = conn.cursor()
            
            # Count unique models and placements
            cursor.execute('''
                SELECT COUNT(DISTINCT model_path) as unique_models,
                       COUNT(DISTINCT p.id) as placements
                FROM m2_models m
                LEFT JOIN m2_placements p ON m.id = p.model_id
                WHERE m.wdt_id = ?
            ''', (wdt_id,))
            m2_stats = cursor.fetchone()
            
            cursor.execute('''
                SELECT COUNT(DISTINCT model_path) as unique_models,
                       COUNT(DISTINCT p.id) as placements
                FROM wmo_models m
                LEFT JOIN wmo_placements p ON m.id = p.model_id
                WHERE m.wdt_id = ?
            ''', (wdt_id,))
            wmo_stats = cursor.fetchone()
            
            cursor.execute('''
                SELECT COUNT(DISTINCT texture_path)
                FROM wdt_textures
                WHERE wdt_id = ?
            ''', (wdt_id,))
            texture_count = cursor.fetchone()[0]
            
            # Get per-tile statistics
            cursor.execute('''
                SELECT t.tile_x, t.tile_y,
                       COUNT(DISTINCT m2.model_path) as m2_models,
                       COUNT(DISTINCT wmo.model_path) as wmo_models,
                       COUNT(DISTINCT tex.texture_path) as textures,
                       COUNT(DISTINCT m2p.id) as m2_placements,
                       COUNT(DISTINCT wmop.id) as wmo_placements
                FROM map_tiles t
                LEFT JOIN m2_placements m2p ON t.wdt_id = m2p.wdt_id AND t.tile_x = m2p.tile_x AND t.tile_y = m2p.tile_y
                LEFT JOIN m2_models m2 ON m2p.model_id = m2.id
                LEFT JOIN wmo_placements wmop ON t.wdt_id = wmop.wdt_id AND t.tile_x = wmop.tile_x AND t.tile_y = wmop.tile_y
                LEFT JOIN wmo_models wmo ON wmop.model_id = wmo.id
                LEFT JOIN wdt_textures tex ON t.wdt_id = tex.wdt_id AND t.tile_x = tex.tile_x AND t.tile_y = tex.tile_y
                WHERE t.wdt_id = ?
                GROUP BY t.tile_x, t.tile_y
            ''', (wdt_id,))
            tile_stats = cursor.fetchall()
            
            # Output results
            print("\nAnalysis Complete!")
            print("=" * 50)
            print(f"Format: {'Alpha' if is_alpha else 'Retail'} WDT")
            print(f"Database: {db_path}")
            print("\nOverall Statistics:")
            print(f"Active Tiles: {active_tiles}")
            print(f"M2 Models: {m2_stats[0]} unique models with {m2_stats[1]} placements")
            print(f"WMO Models: {wmo_stats[0]} unique models with {wmo_stats[1]} placements")
            print(f"Unique Textures: {texture_count}")
            
            if tile_stats:
                print("\nPer-Tile Summary (max counts):")
                max_m2_models = max(s[2] for s in tile_stats)
                max_wmo_models = max(s[3] for s in tile_stats)
                max_textures = max(s[4] for s in tile_stats)
                max_m2_placements = max(s[5] for s in tile_stats)
                max_wmo_placements = max(s[6] for s in tile_stats)
                print(f"  M2 Models: {max_m2_models}")
                print(f"  WMO Models: {max_wmo_models}")
                print(f"  Textures: {max_textures}")
                print(f"  M2 Placements: {max_m2_placements}")
                print(f"  WMO Placements: {max_wmo_placements}")
            
            print(f"\nChunk Order: {', '.join(chunk_order)}")
            if os.path.exists(log_filename) and os.path.getsize(log_filename) > 0:
                print(f"Errors logged to: {log_filename}")
            
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
