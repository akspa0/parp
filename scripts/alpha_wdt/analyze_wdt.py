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
                            # Store ADT chunk offsets with enhanced information
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
                            
                            # Process MCNK data
                            if 'mcnk_data' in tile:
                                print(f"Processing MCNK data for tile ({x}, {y})")
                                try:
                                    # Parse MCNK data with proper Alpha format handling
                                    chunk_ref = ChunkRef(
                                        offset=tile['offset'],
                                        size=tile['size'],
                                        magic='MCNK',
                                        header_offset=tile['offset']
                                    )
                                    mcnk = wdt.parse_mcnk(chunk_ref, is_alpha=is_alpha)
                                    
                                    # Get texture information first
                                    texture_info = {}
                                    if is_alpha:
                                        # For Alpha format, check MTEX chunks
                                        for chunk_ref, mtex_data in wdt.get_chunks_by_type('MTEX'):
                                            mtex_info = parse_mtex(mtex_data)
                                            for i, tex_path in enumerate(mtex_info['textures']):
                                                texture_info[i] = {
                                                    'path': tex_path,
                                                    'flags': {'has_alpha': False, 'is_terrain': True}
                                                }
                                    
                                    # Get MCNK header info
                                    if is_alpha:
                                        mcnk_info = {
                                            'flags': mcnk.header.flags,
                                            'n_layers': mcnk.header.n_layers,
                                            'n_doodad_refs': mcnk.header.n_doodad_refs,
                                            'mcvt_offset': mcnk.mcvt_offset,
                                            'mcnr_offset': 0,  # Not in Alpha
                                            'mcly_offset': mcnk.mcly_offset,
                                            'mcrf_offset': mcnk.mcrf_offset,
                                            'mcal_offset': 0,  # Not in Alpha
                                            'mcsh_offset': 0,  # Not in Alpha
                                            'mclq_offset': mcnk.mclq_offset,
                                            'area_id': mcnk.header.area_id,
                                            'holes': 0,  # Not in Alpha
                                            'liquid_size': 0,  # Will be calculated from actual data
                                            'is_alpha': True,
                                            'textures': texture_info  # Add texture info
                                        }
                                    else:
                                        mcnk_info = {
                                            'flags': mcnk.header.flags,
                                            'n_layers': mcnk.header.n_layers,
                                            'n_doodad_refs': mcnk.header.n_doodad_refs,
                                            'mcvt_offset': mcnk.header.ofs_height,
                                            'mcnr_offset': mcnk.header.ofs_normal,
                                            'mcly_offset': mcnk.header.ofs_layer,
                                            'mcrf_offset': mcnk.header.ofs_refs,
                                            'mcal_offset': mcnk.header.ofs_alpha,
                                            'mcsh_offset': mcnk.header.ofs_shadow,
                                            'mclq_offset': mcnk.header.ofs_liquid,
                                            'area_id': mcnk.header.area_id,
                                            'holes': mcnk.header.holes_low_res,
                                            'liquid_size': mcnk.header.size_liquid,
                                            'is_alpha': False,
                                            'textures': texture_info  # Add texture info
                                        }
                                    
                                    mcnk_id = insert_tile_mcnk(conn, wdt_id, x, y, mcnk_info)
                                    
                                    try:
                                        # Process height map using enhanced methods
                                        height_map = mcnk.get_height_map()
                                        if height_map:
                                            insert_height_map(conn, mcnk_id, height_map)
                                            logging.info(f"Inserted height map data for tile ({x}, {y})")
                                        
                                        # Process layers and textures
                                        layers = mcnk.get_layer_info()
                                        if layers:
                                            for i, layer in enumerate(layers):
                                                # Insert layer info
                                                insert_tile_layer(
                                                    conn, mcnk_id, i,
                                                    layer['texture_id'],
                                                    layer['flags'],
                                                    layer['effect_id']
                                                )
                                                
                                                # Insert texture info
                                                texture_path = f"tileset_{layer['texture_id']:03d}"  # Default name if not found
                                                if 'textures' in mcnk_info and layer['texture_id'] in mcnk_info['textures']:
                                                    texture_info = mcnk_info['textures'][layer['texture_id']]
                                                    texture_path = texture_info.get('path', texture_path)
                                                
                                                insert_texture(
                                                    conn, wdt_id, x, y,
                                                    texture_path,
                                                    i,  # layer_index
                                                    0,  # blend_mode (not in Alpha)
                                                    1 if layer['flags'] & 0x1 else 0,  # has_alpha
                                                    0,  # is_compressed (not in Alpha)
                                                    layer['effect_id'],
                                                    layer['flags']
                                                )
                                            logging.info(f"Inserted {len(layers)} layers for tile ({x}, {y})")
                                        
                                        # Process liquid data using enhanced methods
                                        liquid_info = mcnk.get_liquid_data()
                                        if liquid_info:
                                            liquid_type, liquid_heights = liquid_info
                                            # Map flags to liquid types for Alpha format
                                            if is_alpha and isinstance(mcnk.header.flags, int):
                                                if mcnk.header.flags & 0x4:  # RIVER
                                                    liquid_type = 1  # Water
                                                elif mcnk.header.flags & 0x8:  # OCEAN
                                                    liquid_type = 2  # Ocean
                                                elif mcnk.header.flags & 0x10:  # MAGMA
                                                    liquid_type = 3  # Magma
                                                elif mcnk.header.flags & 0x20:  # SLIME
                                                    liquid_type = 4  # Slime
                                            insert_liquid_data(conn, mcnk_id, liquid_type, liquid_heights)
                                            logging.info(f"Inserted liquid data for tile ({x}, {y})")
                                    except Exception as e:
                                        logging.error(f"Error processing MCNK subchunks for tile ({x}, {y}): {e}")
                                except Exception as e:
                                    logging.error(f"Error processing MCNK chunk for tile ({x}, {y}): {e}")
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
