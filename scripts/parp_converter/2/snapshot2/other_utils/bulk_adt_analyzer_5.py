import os
import re
import sys
import sqlite3
import struct
import logging
from datetime import datetime
from adt_db import setup_database, insert_adt_record, insert_texture, insert_m2_model, insert_wmo_model, insert_mddf, insert_modf, insert_mcnk_data, insert_mcvt_data, insert_mcnr_data, insert_mcly_data, insert_mcal_data, insert_mcsh_data, insert_mclq_data, insert_mccv_data
from decode_chunks import decode_MCNK, decode_MCVT, decode_MCNR, decode_MCLY, decode_MCAL, decode_MCSH, decode_MCLQ, decode_MCCV, decode_MTEX, decode_MDDF

# Generate a timestamp for this run
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Configure logging for the parser
parser_log_filename = f"adt_parser_{timestamp}.log"
logging.basicConfig(
    filename=parser_log_filename,
    filemode='w',
    format='%(asctime)s [%(levelname)s] %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Configure logging for missing files
missing_log_filename = f"missing_files_{timestamp}.log"
missing_logger = logging.getLogger('missing_files')
missing_file_handler = logging.FileHandler(missing_log_filename, mode='w')
missing_file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
missing_logger.addHandler(missing_file_handler)
missing_logger.setLevel(logging.INFO)

def read_c_string_list(data):
    strings = data.split(b'\0')
    return [s.decode('utf-8', 'replace') for s in strings if s]

def load_name_list(base_block, offsets):
    names = []
    for off in offsets:
        if off >= len(base_block):
            names.append("<invalid offset>")
            continue
        end = base_block.find(b'\0', off)
        if end == -1:
            name = base_block[off:].decode('utf-8', 'replace')
        else:
            name = base_block[off:end].decode('utf-8', 'replace')
        names.append(name)
    return names

def try_parse_chunks(data, reverse_names=False):
    pos = 0
    size = len(data)
    chunks = []
    while pos + 8 <= size:
        chunk_name_raw = data[pos:pos+4]
        chunk_name = chunk_name_raw[::-1] if reverse_names else chunk_name_raw
        if pos+8 > size:
            break
        chunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]
        if pos+8+chunk_size > size:
            break
        chunk_data = data[pos+8:pos+8+chunk_size]
        chunks.append((chunk_name, chunk_data))
        pos += 8 + chunk_size
        if len(chunks) > 10:
            break
    return chunks

def detect_chunk_name_reversal(data):
    normal_chunks = try_parse_chunks(data, reverse_names=False)
    reversed_chunks = try_parse_chunks(data, reverse_names=True)

    normal_known = any(c[0] in [b'MVER', b'MHDR', b'MCIN', b'MTEX'] for c in normal_chunks)
    reversed_known = any(c[0] in [b'MVER', b'MHDR', b'MCIN', b'MTEX'] for c in reversed_chunks)

    if normal_known and not reversed_known:
        logger.debug("Detected normal chunk name orientation.")
        return False
    elif reversed_known and not normal_known:
        logger.debug("Detected reversed chunk name orientation.")
        return True
    else:
        logger.warning("Unable to definitively detect chunk name orientation. Assuming normal.")
        return False

def parse_adt(file_path):
    with open(file_path, 'rb') as f:
        data = f.read()

    reverse_names = detect_chunk_name_reversal(data)

    pos = 0
    size = len(data)

    have_MVER = False
    have_MHDR = False
    have_MCIN = False
    have_MTEX = False
    have_MMDX = False
    have_MMID = False

    textures = []
    mmdx_block = b''
    mmid_offsets = []
    mwmo_block = b''
    mwid_offsets = []
    m2_placements = []
    wmo_placements = []
    adt_version = None
    mcnk_chunks = []

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
        pos += 8 + chunk_size

        logger.debug(f"Found chunk: {chunk_name} Size: {chunk_size}")

        decoded_data = None
        if chunk_name == b'MVER':
            have_MVER = True
            adt_version = struct.unpack('<I', chunk_data[0:4])[0]
            logger.debug(f"ADT version: {adt_version}")
        elif chunk_name == b'MHDR':
            have_MHDR = True
        elif chunk_name == b'MCIN':
            have_MCIN = True
        elif chunk_name == b'MTEX':
            have_MTEX = True
            decoded_data, _ = decode_MTEX(chunk_data)
            textures = decoded_data.get('textures', [])
            logger.debug(f"Extracted {len(textures)} textures.")
        elif chunk_name == b'MMDX':
            have_MMDX = True
            mmdx_block = chunk_data
            logger.debug(f"MMDX block length: {len(mmdx_block)}")
        elif chunk_name == b'MMID':
            have_MMID = True
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
            decoded_data, _ = decode_MDDF(chunk_data)
            for entry in decoded_data.get('entries', []):
                m2_placements.append({
                    'nameId': entry['nameId'],
                    'uniqueId': entry['uniqueId'],
                    'position': (entry['position']['x'], entry['position']['y'], entry['position']['z']),
                    'rotation': (entry['rotation']['x'], entry['rotation']['y'], entry['rotation']['z']),
                    'scale': entry['scale'] / 1024.0,
                    'flags': entry['flags']
                })
            logger.debug(f"Extracted {len(m2_placements)} MDDF entries.")
        elif chunk_name == b'MODF':
            count = len(chunk_data) // 64
            logger.debug(f"Extracting {count} MODF entries.")
            for i in range(count):
                entry_data = chunk_data[i*64:(i+1)*64]
                (nameId, uniqueId) = struct.unpack('<II', entry_data[0:8])
                posx, posy, posz = struct.unpack('<fff', entry_data[8:20])
                rotx, roty, rotz = struct.unpack('<fff', entry_data[20:32])
                lx, ly, lz = struct.unpack('<fff', entry_data[32:44])
                ux, uy, uz = struct.unpack('<fff', entry_data[44:56])
                flags, doodadSet, nameSet, scale = struct.unpack('<HHHH', entry_data[56:64])
                wmo_placements.append({
                    'nameId': nameId,
                    'uniqueId': uniqueId,
                    'position': (posx, posy, posz),
                    'rotation': (rotx, roty, rotz),
                    'extents_lower': (lx, ly, lz),
                    'extents_upper': (ux, uy, uz),
                    'flags': flags,
                    'doodadSet': doodadSet,
                    'nameSet': nameSet,
                    'scale': scale / 1024.0
                })
        elif chunk_name == b'MCNK':
            decoded_data, _ = decode_MCNK(chunk_data)
            mcnk_chunks.append(decoded_data)
        else:
            logger.debug(f"Unrecognized chunk: {chunk_name}. Possibly not needed.")

    m2_names = []
    if have_MMDX and have_MMID and mmid_offsets:
        m2_names = load_name_list(mmdx_block, mmid_offsets)
        logger.debug(f"Resolved {len(m2_names)} M2 model names.")
    else:
        if have_MMDX and have_MMID and not mmid_offsets:
            logger.warning("MMID offsets empty. No M2 model names resolved.")

    wmo_names = []
    if mwmo_block and mwid_offsets:
        wmo_names = load_name_list(mwmo_block, mwid_offsets)
        logger.debug(f"Resolved {len(wmo_names)} WMO model names.")
    else:
        if wmo_placements and (not mwmo_block or not mwid_offsets):
            logger.warning("MODF present without MWMO/MWID references.")

    for m in m2_placements:
        model_name = m2_names[m['nameId']] if (0 <= m['nameId'] < len(m2_names)) else ""
        m['model_name'] = model_name

    for w in wmo_placements:
        wmo_name = wmo_names[w['nameId']] if (0 <= w['nameId'] < len(wmo_names)) else ""
        w['wmo_name'] = wmo_name

    if not textures and not m2_placements and not wmo_placements and not mcnk_chunks:
        logger.warning(f"No textures, models, placements or MCNK data found in {file_path}.")

    return {
        'adt_version': adt_version,
        'textures': textures,
        'm2_models': m2_names,
        'wmo_models': wmo_names,
        'mddf': m2_placements,
        'modf': wmo_placements,
        'mcnk': mcnk_chunks
    }

def normalize_filename(fname):
    # Skip invalid or empty filenames immediately
    if not fname or fname == "<invalid offset>":
        return ""

    fname_norm = fname.lower().replace('\\', '/')
    # Remove leading ./ or /
    fname_norm = fname_norm.lstrip('./').lstrip('/')
    # Collapse multiple slashes
    fname_norm = re.sub('/+', '/', fname_norm)
    return fname_norm

def check_file_in_listfile(fname, known_good_files):
    fname_norm = normalize_filename(fname)
    if fname_norm == "":
        # Empty or invalid offset
        return True  # Treat as found so we don't log it as missing

    # Always convert .mdx to .m2 before checking
    if fname_norm.endswith('.mdx'):
        fname_norm = fname_norm[:-4] + '.m2'

    return fname_norm in known_good_files

def write_uid_file(directory, max_uid):
    ini_path = os.path.join(directory, 'uid.ini')
    with open(ini_path, 'w') as f:
        f.write(f"max_unique_id={max_uid}\n")

def main(directory, listfile_path, db_path="analysis.db"):
    logger.info(f"Starting analysis of ADT files in {directory}")
    conn = setup_database(db_path)

    folder_name = os.path.basename(os.path.normpath(directory)).lower()
    pattern = re.compile(r'^(?:.*?)(\d+)_(\d+)\.adt$', re.IGNORECASE)

    # Load known-good listfile - format: <FileID>;<file path>
    known_good_files = set()
    if os.path.exists(listfile_path):
        with open(listfile_path, 'r', encoding='utf-8', errors='replace') as lf:
            for line in lf:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(';', 1)
                if len(parts) < 2:
                    continue
                filename_col = parts[1].strip()
                norm = normalize_filename(filename_col)
                if norm:
                    known_good_files.add(norm)
        logger.info(f"Loaded {len(known_good_files)} known-good filenames from {listfile_path}.")
    else:
        logger.error(f"Listfile {listfile_path} does not exist. Missing file checks will fail.")

    all_unique_ids = []
    missing_files_reported = set()  # to prevent duplicates

    def check_and_log_missing(fname, adt_fname):
        if known_good_files and fname and fname != "<invalid offset>":
            # Only log if truly missing after normalization and .mdx->.m2 conversion
            if not check_file_in_listfile(fname, known_good_files):
                key = (normalize_filename(fname), adt_fname)
                if key[0] and key not in missing_files_reported:
                    missing_files_reported.add(key)
                    missing_logger.info(f"Missing file: {fname} referenced by {adt_fname}")

    for filename in os.listdir(directory):
        if filename.lower().endswith(".adt"):
            match = pattern.search(filename)
            if not match:
                logger.warning(f"Skipping {filename}, does not match pattern _X_Y.adt")
                continue
            x, y = match.groups()
            x, y = int(x), int(y)

            filepath = os.path.join(directory, filename)
            parsed = parse_adt(filepath)

            # Insert into adt_files
            adt_id = insert_adt_record(conn, filename, folder_name, x, y)

            # Check textures
            for tex in parsed['textures']:
                insert_texture(conn, adt_id, tex)
                check_and_log_missing(tex, filename)

            # Check M2 models
            for mm in parsed['m2_models']:
                insert_m2_model(conn, adt_id, mm)
                check_and_log_missing(mm, filename)

            # Check WMO models
            for wm in parsed['wmo_models']:
                insert_wmo_model(conn, adt_id, wm)
                check_and_log_missing(wm, filename)

            # Check MDDF placements
            for m in parsed['mddf']:
                insert_mddf(conn, adt_id, m['uniqueId'], m['model_name'], m['position'], m['rotation'], m['scale'], m['flags'])
                all_unique_ids.append(m['uniqueId'])
                check_and_log_missing(m['model_name'], filename)

            # Check MODF placements
            for w in parsed['modf']:
                insert_modf(conn, adt_id, w['uniqueId'], w['wmo_name'], w['position'], w['rotation'], w['scale'], w['flags'])
                all_unique_ids.append(w['uniqueId'])
                check_and_log_missing(w['wmo_name'], filename)

            # Process MCNK chunks
            for mcnk_data in parsed.get('mcnk', []):
                header = mcnk_data.get('header', {})
                sub_chunks = mcnk_data.get('sub_chunks', {})

                mcnk_id = insert_mcnk_data(conn, adt_id, header.get('index_x'), header.get('index_y'),
                                       sum(1 << i for i, flag in enumerate(header.get('flags', {}).values()) if flag),
                                       1 if 'MCVT' in sub_chunks else 0,
                                       1 if 'MCNR' in sub_chunks else 0,
                                       1 if 'MCLQ' in sub_chunks else 0)

                if 'MCVT' in sub_chunks:
                    insert_mcvt_data(conn, mcnk_id, sub_chunks['MCVT'].get('heights'))
                if 'MCNR' in sub_chunks:
                    insert_mcnr_data(conn, mcnk_id, sub_chunks['MCNR'].get('normals'))
                if 'MCLY' in sub_chunks:
                    insert_mcly_data(conn, mcnk_id, sub_chunks['MCLY'].get('layers'))
                if 'MCAL' in sub_chunks:
                    insert_mcal_data(conn, mcnk_id, sub_chunks['MCAL'].get('alpha_map'), 1 if sub_chunks['MCAL'].get('mode', {}).get('compressed') else 0)
                if 'MCSH' in sub_chunks:
                    insert_mcsh_data(conn, mcnk_id, sub_chunks['MCSH'].get('shadow_map'))
                if 'MCLQ' in sub_chunks:
                    insert_mclq_data(conn, mcnk_id, sub_chunks['MCLQ'].get('heights'))
                if 'MCCV' in sub_chunks:
                    insert_mccv_data(conn, mcnk_id, sub_chunks['MCCV'].get('vertex_colors'))

            conn.commit()
            logger.info(f"Processed {filename}")

    # Check uniqueID uniqueness
    if len(all_unique_ids) != len(set(all_unique_ids)):
        logger.warning("Not all uniqueIDs are unique! This violates the specification.")

    # Store max uniqueID in uid.ini
    max_uid = max(all_unique_ids) if all_unique_ids else 0
    write_uid_file(directory, max_uid)
    logger.info(f"Maximum uniqueID in {directory} is {max_uid}. Written to uid.ini.")

    conn.close()
    logger.info("Analysis complete.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python bulk_adt_analysis.py <directory_of_adts> <listfile_path> [database_path]")
        sys.exit(1)

    directory = sys.argv[1]
    listfile_path = sys.argv[2]
    db_path = "analysis.db"
    if len(sys.argv) > 3:
        db_path = sys.argv[3]
    main(directory, listfile_path, db_path)