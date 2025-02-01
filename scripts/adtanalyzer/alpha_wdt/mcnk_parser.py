import sqlite3
import logging
import array
from typing import Optional, Tuple, List
from chunk_handler import WDTFile, ChunkRef
from adt_parser.mcnk_decoders import MCNKChunk

def process_mcnk_data(
    conn: sqlite3.Connection,
    wdt_id: int,
    tile_x: int,
    tile_y: int,
    wdt_file: WDTFile,
    chunk_ref: ChunkRef,
    is_alpha: bool = False
) -> Optional[int]:
    """
    Process MCNK data and store in database.
    Returns the mcnk_id if successful, None otherwise.
    
    Args:
        conn: Database connection
        wdt_id: WDT file ID
        tile_x, tile_y: Tile coordinates
        wdt_file: WDTFile instance
        chunk_ref: Reference to MCNK chunk
        is_alpha: Whether this is Alpha format
    """
    try:
        # Parse MCNK data
        mcnk = wdt_file.parse_mcnk(chunk_ref, is_alpha=is_alpha)
        if not mcnk:
            logging.error(f"Failed to parse MCNK data for tile ({tile_x}, {tile_y})")
            return None

        # Get MCNK header info
        if is_alpha:
            mcvt_offset = mcnk.mcvt_offset
            mcly_offset = mcnk.mcly_offset
            mcrf_offset = mcnk.mcrf_offset
            mclq_offset = mcnk.mclq_offset
        else:
            mcvt_offset = mcnk.header.ofs_height
            mcly_offset = mcnk.header.ofs_layer
            mcrf_offset = mcnk.header.ofs_refs
            mclq_offset = mcnk.header.ofs_liquid

        mcnk_info = {
            'flags': mcnk.header.flags,
            'n_layers': mcnk.header.n_layers,
            'n_doodad_refs': mcnk.header.n_doodad_refs,
            'mcvt_offset': mcvt_offset,
            'mcnr_offset': 0 if is_alpha else mcnk.header.ofs_normal,
            'mcly_offset': mcly_offset,
            'mcrf_offset': mcrf_offset,
            'mcal_offset': 0 if is_alpha else mcnk.header.ofs_alpha,
            'mcsh_offset': 0 if is_alpha else mcnk.header.ofs_shadow,
            'mclq_offset': mclq_offset,
            'area_id': mcnk.header.area_id,
            'holes': 0 if is_alpha else mcnk.header.holes_low_res,
            'liquid_size': 0 if is_alpha else mcnk.header.size_liquid,
            'is_alpha': is_alpha
        }

        # Insert MCNK info
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO tile_mcnk (
            wdt_id, tile_x, tile_y, flags, layers, doodad_refs,
            mcvt_offset, mcnr_offset, mcly_offset, mcrf_offset,
            mcal_offset, mcsh_offset, mclq_offset,
            area_id, holes, liquid_size, is_alpha
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            wdt_id, tile_x, tile_y,
            mcnk_info['flags'], mcnk_info['n_layers'], mcnk_info['n_doodad_refs'],
            mcnk_info['mcvt_offset'], mcnk_info['mcnr_offset'], mcnk_info['mcly_offset'],
            mcnk_info['mcrf_offset'], mcnk_info['mcal_offset'], mcnk_info['mcsh_offset'],
            mcnk_info['mclq_offset'], mcnk_info['area_id'], mcnk_info['holes'],
            mcnk_info['liquid_size'], mcnk_info['is_alpha']
        ))
        mcnk_id = cursor.lastrowid
        conn.commit()

        # Process height map
        height_map = mcnk.get_height_map()
        if height_map:
            process_height_map(conn, mcnk_id, height_map)
            logging.info(f"Processed height map for tile ({tile_x}, {tile_y})")

        # Process layers
        layers = mcnk.get_layer_info()
        if layers:
            process_layers(conn, mcnk_id, layers, is_alpha)
            logging.info(f"Processed {len(layers)} layers for tile ({tile_x}, {tile_y})")

        # Process liquid data
        liquid_info = mcnk.get_liquid_data()
        if liquid_info:
            process_liquid_data(conn, mcnk_id, liquid_info, mcnk.header.flags if is_alpha else None)
            logging.info(f"Processed liquid data for tile ({tile_x}, {tile_y})")

        return mcnk_id

    except Exception as e:
        logging.error(f"Error processing MCNK data for tile ({tile_x}, {tile_y}): {e}")
        return None

def process_height_map(conn: sqlite3.Connection, mcnk_id: int, height_data: array.array) -> None:
    """Process and store height map data"""
    try:
        # Calculate height statistics
        heights = list(height_data)
        min_height = min(heights)
        max_height = max(heights)
        avg_height = sum(heights) / len(heights)

        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO height_map_info (
            tile_mcnk_id, height_data, grid_size,
            min_height, max_height, avg_height
        ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            mcnk_id,
            height_data.tobytes(),
            len(heights),
            min_height,
            max_height,
            avg_height
        ))
        conn.commit()

    except Exception as e:
        logging.error(f"Error processing height map for MCNK {mcnk_id}: {e}")

def process_layers(conn: sqlite3.Connection, mcnk_id: int, layers: List[dict], is_alpha: bool) -> None:
    """Process and store layer information using batch operations"""
    try:
        cursor = conn.cursor()
        # Prepare batch data
        layer_data = [
            (mcnk_id, i, layer['texture_id'], layer['flags'],
             0 if is_alpha else layer.get('effect_id', 0))
            for i, layer in enumerate(layers)
        ]
        
        # Batch insert
        cursor.executemany('''
        INSERT INTO tile_layers (
            tile_mcnk_id, layer_index, texture_id,
            flags, effect_id
        ) VALUES (?, ?, ?, ?, ?)
        ''', layer_data)
        
        conn.commit()
        
        if len(layers) > 0:
            print(f"Processed {len(layers)} layers for MCNK {mcnk_id}")

    except Exception as e:
        logging.error(f"Error processing layers for MCNK {mcnk_id}: {e}")

def process_liquid_data(
    conn: sqlite3.Connection,
    mcnk_id: int,
    liquid_info: Tuple[int, array.array],
    alpha_flags: Optional[int] = None
) -> None:
    """Process and store liquid data"""
    try:
        liquid_type, liquid_heights = liquid_info
        
        # For Alpha format, determine liquid type from flags
        if alpha_flags is not None:
            if alpha_flags & 0x4:    # RIVER
                liquid_type = 1
            elif alpha_flags & 0x8:  # OCEAN
                liquid_type = 2
            elif alpha_flags & 0x10: # MAGMA
                liquid_type = 3
            elif alpha_flags & 0x20: # SLIME
                liquid_type = 4

        # Calculate height statistics
        heights = list(liquid_heights)
        min_height = min(heights) if heights else 0.0
        max_height = max(heights) if heights else 0.0

        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO liquid_data (
            tile_mcnk_id, liquid_type, liquid_data,
            min_height, max_height
        ) VALUES (?, ?, ?, ?, ?)
        ''', (
            mcnk_id,
            liquid_type,
            liquid_heights.tobytes(),
            min_height,
            max_height
        ))
        conn.commit()

    except Exception as e:
        logging.error(f"Error processing liquid data for MCNK {mcnk_id}: {e}")