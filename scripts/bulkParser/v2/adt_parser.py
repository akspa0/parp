"""
ADT File Parsing Logic
Contains functions for parsing ADT files and their chunks
"""

import os
import re
import struct
import logging
from collections import defaultdict

# Import local modules
from utils import (detect_chunk_name_reversal, load_name_list, normalize_filename, 
                  check_file_in_listfile, repair_file_path, group_adt_files)
from chunk_decoders import CHUNK_DECODERS
from database import (insert_adt_record, insert_texture, insert_m2_model, insert_wmo_model,
                     insert_mddf, insert_modf, insert_mcnk_data, insert_mcvt_data,
                     insert_mcnr_data, insert_mcly_data, insert_mcal_data, insert_mcsh_data,
                     insert_mclq_data, insert_mccv_data, insert_mclv_data, insert_mcdd_data,
                     insert_mamp_data, insert_mtxf_data, insert_mtxp_data, insert_mh2o_data,
                     insert_mcmt_data, insert_mfbo_data)

logger = logging.getLogger("parser")

def load_listfile(listfile_path, logger):
    """
    Load listfile and create mappings for FileDataIDs
    
    Args:
        listfile_path: Path to the listfile
        logger: Logger instance
        
    Returns:
        Tuple of (known_good_files, file_data_id_map)
    """
    known_good_files = set()
    file_data_id_map = {}  # Map FileDataIDs to paths
    
    if os.path.exists(listfile_path):
        with open(listfile_path, 'r', encoding='utf-8', errors='replace') as lf:
            for line in lf:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(';', 1)
                if len(parts) == 2:
                    try:
                        # Try to parse the FileDataID 
                        file_id = int(parts[0])
                        filename = parts[1].strip()
                        
                        # Add to FileDataID map
                        file_data_id_map[file_id] = filename
                        
                        # Also add to known_good_files for backward compatibility
                        norm = normalize_filename(filename)
                        if norm:
                            known_good_files.add(norm)
                    except ValueError:
                        # If first part isn't an integer, just use the old approach
                        norm = normalize_filename(parts[1])
                        if norm:
                            known_good_files.add(norm)
                else:
                    # Standard filename format without a FileDataID
                    norm = normalize_filename(line)
                    if norm:
                        known_good_files.add(norm)
        
        logger.info(f"Loaded {len(known_good_files)} known-good filenames from {listfile_path}.")
        logger.info(f"Created mapping for {len(file_data_id_map)} FileDataIDs.")
    else:
        logger.error(f"Listfile {listfile_path} does not exist. Missing file checks will fail.")
    
    return known_good_files, file_data_id_map

def parse_adt_file(file_path, reverse_names=None, file_data_id_map=None):
    """Parse a single ADT file and extract its chunks with enhanced decoders"""
    with open(file_path, 'rb') as f:
        data = f.read()

    if reverse_names is None:
        reverse_names = detect_chunk_name_reversal(data)

    file_type = "unknown"
    if "_tex" in file_path.lower():
        file_type = "tex"
    elif "_obj" in file_path.lower():
        file_type = "obj"
    elif "_lod" in file_path.lower():
        file_type = "lod"
    else:
        file_type = "root"
    
    logger.debug(f"Parsing file {file_path} as {file_type} file")

    pos = 0
    size = len(data)

    # Initialize result structure
    result = {
        'adt_version': None,
        'textures': [],
        'texture_fileids': [],
        'm2_models': [],
        'wmo_models': [],
        'mddf': [],
        'modf': [],
        'mcnk': [],
        'file_type': file_type,
        'chunks_present': set()  # Just track which chunks exist, not their content
    }

    # Variables for specific chunks
    mmdx_block = b''
    mmid_offsets = []
    mwmo_block = b''
    mwid_offsets = []
    mdid_texture_ids = []
    mhid_texture_ids = []

    while pos < size:
        if pos + 8 > size:
            break

        chunk_name_raw = data[pos:pos+4]
        chunk_name = chunk_name_raw[::-1] if reverse_names else chunk_name_raw
        if pos+8 > size:
            break
        chunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]
        if pos+8+chunk_size > size:
            logger.error(f"Chunk {chunk_name} extends beyond file size. Corrupt file?")
            break
        chunk_data = data[pos+8:pos+8+chunk_size]
        
        # Store absolute offset for reference
        chunk_offset = pos + 8
        
        pos += 8 + chunk_size

        logger.debug(f"Found chunk: {chunk_name} Size: {chunk_size}")

        # Track which chunks are present
        result['chunks_present'].add(chunk_name)

        # Handle specific chunks
        if chunk_name == b'MVER':
            decoded_data, _ = CHUNK_DECODERS[b'MVER'](chunk_data)
            adt_version = decoded_data.get('version', 0)
            result['adt_version'] = adt_version
            logger.debug(f"ADT version: {adt_version}")
        
        elif chunk_name == b'MTEX':
            decoded_data, _ = CHUNK_DECODERS[b'MTEX'](chunk_data)
            textures = decoded_data.get('textures', [])
            result['textures'].extend(textures)
            logger.debug(f"Extracted {len(textures)} textures.")
        
        elif chunk_name == b'MDID':
            # Battle for Azeroth+ diffuse texture FileDataIDs
            decoded_data, _ = CHUNK_DECODERS[b'MDID'](chunk_data)
            mdid_texture_ids = decoded_data.get('diffuse_texture_ids', [])
            result['texture_fileids'].extend([(file_id, 'diffuse') for file_id in mdid_texture_ids])
            logger.debug(f"Extracted {len(mdid_texture_ids)} diffuse texture FileDataIDs.")
        
        elif chunk_name == b'MHID':
            # Battle for Azeroth+ height texture FileDataIDs
            decoded_data, _ = CHUNK_DECODERS[b'MHID'](chunk_data)
            mhid_texture_ids = decoded_data.get('height_texture_ids', [])
            result['texture_fileids'].extend([(file_id, 'height') for file_id in mhid_texture_ids])
            logger.debug(f"Extracted {len(mhid_texture_ids)} height texture FileDataIDs.")
        
        elif chunk_name == b'MMDX':
            mmdx_block = chunk_data
            logger.debug(f"MMDX block length: {len(mmdx_block)}")
        
        elif chunk_name == b'MMID':
            count = len(chunk_data)//4
            mmid_offsets = list(struct.unpack('<' + 'I'*count, chunk_data))
            logger.debug(f"Extracted {len(mmid_offsets)} MMID offsets.")
        
        elif chunk_name == b'MWMO':
            mwmo_block = chunk_data
            logger.debug(f"MWMO block length: {len(mwmo_block)}")
        
        elif chunk_name == b'MWID':
            count = len(chunk_data)//4
            mwid_offsets = list(struct.unpack('<' + 'I'*count, chunk_data))
            logger.debug(f"Extracted {len(mwid_offsets)} MWID offsets.")
        
        elif chunk_name == b'MDDF':
            decoded_data, _ = CHUNK_DECODERS[b'MDDF'](chunk_data)
            for entry in decoded_data.get('entries', []):
                m2_placement = {
                    'nameId': entry['nameId'],
                    'uniqueId': entry['uniqueId'],
                    'position': (entry['position']['x'], entry['position']['y'], entry['position']['z']),
                    'rotation': (entry['rotation']['x'], entry['rotation']['y'], entry['rotation']['z']),
                    'scale': entry['scale'] / 1024.0,
                    'flags': entry['flags'],
                    'is_file_data_id': entry.get('is_file_data_id', False)
                }
                result['mddf'].append(m2_placement)
            logger.debug(f"Extracted {len(result['mddf'])} MDDF entries.")
        
        elif chunk_name == b'MODF':
            decoded_data, _ = CHUNK_DECODERS[b'MODF'](chunk_data)
            for entry in decoded_data.get('entries', []):
                wmo_placement = {
                    'nameId': entry['nameId'],
                    'uniqueId': entry['uniqueId'],
                    'position': (entry['position']['x'], entry['position']['y'], entry['position']['z']),
                    'rotation': (entry['rotation']['x'], entry['rotation']['y'], entry['rotation']['z']),
                    'extents_lower': (entry['extents_lower']['x'], entry['extents_lower']['y'], entry['extents_lower']['z']),
                    'extents_upper': (entry['extents_upper']['x'], entry['extents_upper']['y'], entry['extents_upper']['z']),
                    'flags': entry['flags'],
                    'doodadSet': entry['doodadSet'],
                    'nameSet': entry['nameSet'],
                    'scale': entry['scale'] / 1024.0,
                    'is_file_data_id': entry.get('is_file_data_id', False)
                }
                result['modf'].append(wmo_placement)
            logger.debug(f"Extracted {len(result['modf'])} MODF entries.")
        
        elif chunk_name == b'MCNK':
            # Use enhanced MCNK decoder that properly extracts all sub-chunks
            decoded_data, _ = CHUNK_DECODERS[b'MCNK'](chunk_data, chunk_offset)
            result['mcnk'].append(decoded_data)
            logger.debug(f"Extracted MCNK with {len(decoded_data.get('sub_chunks', {}))} sub-chunks.")
        
        elif chunk_name == b'MFBO':
            # Flying bounding box
            decoded_data, _ = CHUNK_DECODERS[b'MFBO'](chunk_data)
            logger.debug(f"Extracted MFBO data")
            result['mfbo'] = decoded_data
            
        elif chunk_name in CHUNK_DECODERS:
            # Generic handler for other known chunks
            decoded_data, _ = CHUNK_DECODERS[chunk_name](chunk_data)
            result[chunk_name.decode('utf-8').lower()] = decoded_data
            logger.debug(f"Extracted {chunk_name.decode('utf-8')} data")
            # Process model names after all chunks are parsed
    
    m2_names = []
    if mmdx_block and mmid_offsets:
        m2_names = load_name_list(mmdx_block, mmid_offsets)
        result['m2_models'].extend(m2_names)
        logger.debug(f"Resolved {len(m2_names)} M2 model names.")

    wmo_names = []
    if mwmo_block and mwid_offsets:
        wmo_names = load_name_list(mwmo_block, mwid_offsets)
        result['wmo_models'].extend(wmo_names)
        logger.debug(f"Resolved {len(wmo_names)} WMO model names.")

    # Resolve model references in placements
    for m in result['mddf']:
        if m.get('is_file_data_id', False) and file_data_id_map:
            # FileDataID reference - look up in our mapping
            file_id = m['nameId']
            model_name = file_data_id_map.get(file_id, f"FileDataID:{file_id}")
            logger.debug(f"Resolved FileDataID {file_id} to {model_name}")
        else:
            # Traditional nameId reference into m2_names
            model_name = m2_names[m['nameId']] if (0 <= m['nameId'] < len(m2_names)) else ""
        m['model_name'] = model_name

    for w in result['modf']:
        if w.get('is_file_data_id', False) and file_data_id_map:
            # FileDataID reference - look up in our mapping
            file_id = w['nameId']
            wmo_name = file_data_id_map.get(file_id, f"FileDataID:{file_id}")
            logger.debug(f"Resolved FileDataID {file_id} to {wmo_name}")
        else:
            # Traditional nameId reference into wmo_names
            wmo_name = wmo_names[w['nameId']] if (0 <= w['nameId'] < len(wmo_names)) else ""
        w['wmo_name'] = wmo_name

    # Resolve texture FileDataIDs if we have them
    if mdid_texture_ids or mhid_texture_ids:
        texture_paths = []
        for file_id in mdid_texture_ids:
            if file_data_id_map:
                texture_path = file_data_id_map.get(file_id, f"FileDataID:{file_id}")
                texture_paths.append(texture_path)
                logger.debug(f"Resolved diffuse texture FileDataID {file_id} to {texture_path}")
        
        # If we found texture paths from FileDataIDs, use them instead of MTEX entries
        if texture_paths:
            result['textures'] = texture_paths
            logger.debug(f"Using {len(texture_paths)} resolved texture paths from FileDataIDs")

    return result

def parse_adt(file_paths, file_data_id_map=None):
    """
    Parse a single ADT or a set of split ADT files.
    file_paths can be a single file path or a list of related ADT files.
    """
    if isinstance(file_paths, str):
        file_paths = [file_paths]
    
    # Initialize the combined result
    combined_result = {
        'adt_version': None,
        'textures': [],
        'texture_fileids': [],
        'm2_models': [],
        'wmo_models': [],
        'mddf': [],
        'modf': [],
        'mcnk': [],
        'chunks_present': set()
    }
    
    # Determine the reverse_names setting from the first file
    reverse_names = None
    if file_paths:
        with open(file_paths[0], 'rb') as f:
            data = f.read()
        reverse_names = detect_chunk_name_reversal(data)
    
    # Process each file and combine results
    for file_path in file_paths:
        logger.info(f"Parsing file: {file_path}")
        file_result = parse_adt_file(file_path, reverse_names, file_data_id_map)
        
        # Combine results
        if combined_result['adt_version'] is None:
            combined_result['adt_version'] = file_result['adt_version']
        
        combined_result['textures'].extend(file_result['textures'])
        combined_result['texture_fileids'].extend(file_result['texture_fileids'])
        combined_result['m2_models'].extend(file_result['m2_models'])
        combined_result['wmo_models'].extend(file_result['wmo_models'])
        combined_result['mddf'].extend(file_result['mddf'])
        combined_result['modf'].extend(file_result['modf'])
        combined_result['mcnk'].extend(file_result['mcnk'])
        
        # Copy MFBO data if available
        if 'mfbo' in file_result:
            combined_result['mfbo'] = file_result['mfbo']
        
        # Track which chunks are present
        combined_result['chunks_present'].update(file_result['chunks_present'])
    
    # Remove duplicates where appropriate
    combined_result['textures'] = list(dict.fromkeys(combined_result['textures']))
    combined_result['m2_models'] = list(dict.fromkeys(combined_result['m2_models']))
    combined_result['wmo_models'] = list(dict.fromkeys(combined_result['wmo_models']))
    
    return combined_result

def process_mcnk_chunks(conn, adt_id, mcnk_data):
    """
    Process MCNK chunks and their sub-chunks and store them in the database
    
    Args:
        conn: Database connection
        adt_id: ID of the ADT file in the database
        mcnk_data: Decoded MCNK data from the enhanced decoder
    
    Returns:
        Dictionary of MCNK IDs
    """
    mcnk_ids = {}
    
    header = mcnk_data.get('header', {})
    sub_chunks = mcnk_data.get('sub_chunks', {})
    
    # Calculate flags
    flags = header.get('flags_raw', 0)
    
    # Get position
    position = (0, 0, 0)
    if 'position' in header:
        if isinstance(header['position'], dict):
            position = (header['position'].get('x', 0), 
                       header['position'].get('y', 0), 
                       header['position'].get('z', 0))
    
    # Insert main MCNK record
    mcnk_id = insert_mcnk_data(
        conn, adt_id, 
        header.get('index_x', 0), 
        header.get('index_y', 0),
        flags,
        header.get('areaid', 0),
        position,
        1 if 'MCVT' in sub_chunks else 0,
        1 if 'MCNR' in sub_chunks else 0,
        1 if 'MCLQ' in sub_chunks else 0,
        1 if 'MCSH' in sub_chunks else 0,
        1 if 'MCCV' in sub_chunks else 0,
        1 if 'MCLV' in sub_chunks else 0
    )
    
    # Store this MCNK ID for reference
    key = (header.get('index_x', 0), header.get('index_y', 0))
    mcnk_ids[key] = mcnk_id
    
    # Process each sub-chunk
    if 'MCVT' in sub_chunks:
        heights = sub_chunks['MCVT'].get('heights', [])
        if heights:
            insert_mcvt_data(conn, mcnk_id, heights)
    
    if 'MCNR' in sub_chunks:
        normals = sub_chunks['MCNR'].get('normals', [])
        if normals:
            insert_mcnr_data(conn, mcnk_id, normals)
    
    if 'MCLY' in sub_chunks:
        layers = sub_chunks['MCLY'].get('layers', [])
        for layer in layers:
            insert_mcly_data(conn, mcnk_id, layer)
    
    if 'MCAL' in sub_chunks:
        alpha_map = sub_chunks['MCAL'].get('alpha_map')
        compressed = 1 if sub_chunks['MCAL'].get('mode', {}).get('compressed', False) else 0
        if alpha_map:
            insert_mcal_data(conn, mcnk_id, alpha_map, compressed)
    
    if 'MCSH' in sub_chunks:
        shadow_map = sub_chunks['MCSH'].get('shadow_map')
        if shadow_map:
            insert_mcsh_data(conn, mcnk_id, shadow_map)
    
    if 'MCLQ' in sub_chunks:
        liquid_data = sub_chunks['MCLQ'].get('raw_data')
        if liquid_data:
            insert_mclq_data(conn, mcnk_id, liquid_data)
    
    if 'MCCV' in sub_chunks:
        vertex_colors = sub_chunks['MCCV'].get('vertex_colors')
        if vertex_colors:
            insert_mccv_data(conn, mcnk_id, vertex_colors)
    
    if 'MCLV' in sub_chunks:
        vertex_lighting = sub_chunks['MCLV'].get('vertex_lighting')
        if vertex_lighting:
            insert_mclv_data(conn, mcnk_id, vertex_lighting)
    
    if 'MCDD' in sub_chunks:
        disable_data = sub_chunks['MCDD'].get('disable_data')
        if disable_data:
            insert_mcdd_data(conn, mcnk_id, disable_data)
    
    return mcnk_ids        
def process_global_chunks(conn, adt_id, parsed_data):
    """
    Process global chunks (not within MCNK) and store them in the database
    
    Args:
        conn: Database connection
        adt_id: ID of the ADT file in the database
        parsed_data: Parsed ADT data
    """
    # Check if specific chunks are present and process them
    chunks_present = parsed_data['chunks_present']
    
    # Process MAMP chunk
    if b'MAMP' in chunks_present and 'mamp' in parsed_data:
        decoded_data = parsed_data['mamp']
        insert_mamp_data(conn, adt_id, decoded_data.get('value', 0))
    
    # Process MTXF chunk
    if b'MTXF' in chunks_present and 'mtxf' in parsed_data:
        decoded_data = parsed_data['mtxf']
        texture_flags = parsed_data.get('texture_flags', [])
        if texture_flags:
            # Create a binary representation of the flags
            flags_data = struct.pack('<' + 'I' * len(texture_flags), 
                                    *[flag['raw_flag'] for flag in texture_flags])
            insert_mtxf_data(conn, adt_id, flags_data)
    
    # Process MTXP chunk
    if b'MTXP' in chunks_present and 'mtxp' in parsed_data:
        decoded_data = parsed_data['mtxp']
        # Extract data in a structured format instead of raw bytes
        params = parsed_data.get('texture_params', [])
        if params:
            # Create a binary representation of the parameters
            param_data = b''
            for param in params:
                param_data += struct.pack('<Iffi', param['flags'], 
                                        param['height_scale'], 
                                        param['height_offset'], 
                                        param['padding'])
            insert_mtxp_data(conn, adt_id, param_data)
    
    # Process MH2O chunk
    if b'MH2O' in chunks_present and 'mh2o' in parsed_data:
        decoded_data = parsed_data['mh2o']
        # Extract water data in a structured format
        headers = decoded_data.get('headers', [])
        if headers:
            # Create a binary representation of the water data
            header_data = b''
            for header in headers:
                header_data += struct.pack('<II', header['offset_instances'], 
                                         header['layer_count'])
            insert_mh2o_data(conn, adt_id, header_data)
    
    # Process MCMT chunk
    if b'MCMT' in chunks_present and 'mcmt' in parsed_data:
        decoded_data = parsed_data['mcmt']
        material_ids = decoded_data.get('material_ids', [])
        if material_ids:
            # Create a binary representation of the material IDs
            material_data = struct.pack('<' + 'B' * len(material_ids), *material_ids)
            insert_mcmt_data(conn, adt_id, material_data)
        
    # Process MFBO chunk
    if 'mfbo' in parsed_data:
        mfbo_data = parsed_data['mfbo']
        insert_mfbo_data(
            conn, 
            adt_id, 
            mfbo_data.get('maximum_plane', []),
            mfbo_data.get('minimum_plane', [])
        )

def parse_directory(directory, conn, known_good_files, file_data_id_map, loggers, attempt_repairs=True):
    """
    Parse all ADT files in a directory
    
    Args:
        directory: Directory containing ADT files
        conn: Database connection
        known_good_files: Set of known good file paths
        file_data_id_map: Dictionary mapping FileDataIDs to paths
        loggers: Dictionary containing logger instances
        attempt_repairs: Whether to attempt to repair paths
        
    Returns:
        Tuple of (all_unique_ids, repairs)
    """
    logger = loggers["parser"]
    missing_logger = loggers["missing"]
    
    folder_name = os.path.basename(os.path.normpath(directory)).lower()
    
    all_unique_ids = []
    missing_files_reported = set()  # to prevent duplicates
    repairs = {}  # Track path repairs

    def check_and_log_missing(fname, adt_fname):
        """Check if a file is missing and log it"""
        # Skip FileDataID format references
        if fname and fname.startswith("FileDataID:"):
            return
            
        if known_good_files and fname and fname != "<invalid offset>":
            # Only log if truly missing after normalization and .mdx->.m2 conversion
            if not check_file_in_listfile(fname, known_good_files):
                key = (normalize_filename(fname), adt_fname)
                if key[0] and key not in missing_files_reported:
                    missing_files_reported.add(key)
                    missing_logger.info(f"Missing file: {fname} referenced by {adt_fname}")
                    
                    # Attempt to repair the path
                    if attempt_repairs:
                        repaired = repair_file_path(fname, known_good_files)
                        if repaired:
                            repairs[fname] = repaired
                            missing_logger.info(f"Repaired path: {fname} -> {repaired}")

    # Group related ADT files
    adt_groups = group_adt_files(directory)
    logger.info(f"Found {len(adt_groups)} ADT groups in directory.")

    for base_name, file_paths in adt_groups.items():
        logger.info(f"Processing ADT group: {base_name} with {len(file_paths)} files")
        
        # Extract X and Y coordinates from the base name
        coords_match = re.search(r'(\d+)_(\d+)', base_name)
        if not coords_match:
            logger.warning(f"Could not extract coordinates from {base_name}, skipping")
            continue
            
        x, y = map(int, coords_match.groups())
        
        # Parse the ADT group with FileDataID support
        parsed = parse_adt(file_paths, file_data_id_map)
        
        # Use the first file as the representative name
        representative_name = os.path.basename(file_paths[0])
        
        # Insert into adt_files
        adt_id = insert_adt_record(conn, representative_name, folder_name, x, y, parsed['adt_version'])

        # Process global chunks (no raw data storage)
        process_global_chunks(conn, adt_id, parsed)

        # Check textures from traditional MTEX chunk
        for tex in parsed['textures']:
            insert_texture(conn, adt_id, tex)
            check_and_log_missing(tex, representative_name)
            
        # Handle texture FileDataIDs from MDID/MHID chunks
        for file_id, tex_type in parsed['texture_fileids']:
            tex_path = file_data_id_map.get(file_id, f"FileDataID:{file_id}")
            insert_texture(conn, adt_id, tex_path, file_id, tex_type)
            logger.debug(f"Added texture from FileDataID {file_id}: {tex_path} ({tex_type})")

        # Check M2 models
        for mm in parsed['m2_models']:
            insert_m2_model(conn, adt_id, mm)
            check_and_log_missing(mm, representative_name)

        # Check WMO models
        for wm in parsed['wmo_models']:
            insert_wmo_model(conn, adt_id, wm)
            check_and_log_missing(wm, representative_name)

        # Check MDDF placements (M2 models)
        for m in parsed['mddf']:
            # Check if this is a FileDataID reference
            file_data_id = None
            if m.get('is_file_data_id', False):
                file_data_id = m['nameId']
                
            mddf_id = insert_mddf(conn, adt_id, m['uniqueId'], m['model_name'], 
                               m['position'], m['rotation'], m['scale'], m['flags'],
                               file_data_id)
            all_unique_ids.append(m['uniqueId'])
            check_and_log_missing(m['model_name'], representative_name)

        # Check MODF placements (WMO models)
        for w in parsed['modf']:
            # Check if this is a FileDataID reference
            file_data_id = None
            if w.get('is_file_data_id', False):
                file_data_id = w['nameId']
                
            modf_id = insert_modf(conn, adt_id, w['uniqueId'], w['wmo_name'], 
                               w['position'], w['rotation'], w['scale'], w['flags'],
                               w.get('doodadSet', 0), w.get('nameSet', 0),
                               file_data_id)
            all_unique_ids.append(w['uniqueId'])
            check_and_log_missing(w['wmo_name'], representative_name)

        # Process MCNK chunks (terrain) with enhanced sub-chunk support
        for mcnk_data in parsed.get('mcnk', []):
            process_mcnk_chunks(conn, adt_id, mcnk_data)

        conn.commit()
        logger.info(f"Processed ADT group {base_name}")
    
    return all_unique_ids, repairs