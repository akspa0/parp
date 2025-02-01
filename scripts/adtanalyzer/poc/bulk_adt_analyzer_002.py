import os
import re
import sys
import sqlite3
import struct
import logging
from datetime import datetime

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
            textures = read_c_string_list(chunk_data)
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
            count = len(chunk_data) // 36
            logger.debug(f"Extracting {count} MDDF entries.")
            for i in range(count):
                entry_data = chunk_data[i*36:(i+1)*36]
                nameId, uniqueId = struct.unpack('<II', entry_data[0:8])
                posx, posy, posz = struct.unpack('<fff', entry_data[8:20])
                rotx, roty, rotz = struct.unpack('<fff', entry_data[20:32])
                scale, flags = struct.unpack('<HH', entry_data[32:36])
                m2_placements.append({
                    'nameId': nameId,
                    'uniqueId': uniqueId,
                    'position': (posx, posy, posz),
                    'rotation': (rotx, roty, rotz),
                    'scale': scale / 1024.0,
                    'flags': flags
                })
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

    if not textures and not m2_placements and not wmo_placements:
        logger.warning(f"No textures, models, or placements found in {file_path}.")

    return {
        'adt_version': adt_version,
        'textures': textures,
        'm2_models': m2_names,
        'wmo_models': wmo_names,
        'mddf': m2_placements,
        'modf': wmo_placements
    }

def setup_database(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS adt_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        folder_name TEXT,
        x_coord INTEGER,
        y_coord INTEGER
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS textures (
        adt_id INTEGER,
        texture TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS m2_models (
        adt_id INTEGER,
        model_name TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS wmo_models (
        adt_id INTEGER,
        wmo_name TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS mddf (
        adt_id INTEGER,
        uniqueId INTEGER,
        model_name TEXT,
        posX REAL,
        posY REAL,
        posZ REAL,
        rotX REAL,
        rotY REAL,
        rotZ REAL,
        scale REAL,
        flags INTEGER
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS modf (
        adt_id INTEGER,
        uniqueId INTEGER,
        wmo_name TEXT,
        posX REAL,
        posY REAL,
        posZ REAL,
        rotX REAL,
        rotY REAL,
        rotZ REAL,
        scale REAL,
        flags INTEGER
    )
    """)
    conn.commit()
    return conn

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
    if fname_norm in known_good_files:
        return True
    # If .mdx, try .m2
    if fname_norm.endswith('.mdx'):
        alt = fname_norm[:-4] + '.m2'
        if alt in known_good_files:
            return True
    return False

def write_uid_file(directory, max_uid):
    ini_path = os.path.join(directory, 'uid.ini')
    with open(ini_path, 'w') as f:
        f.write(f"max_unique_id={max_uid}\n")

def main(directory, listfile_path, db_path="analysis.db"):
    logger.info(f"Starting analysis of ADT files in {directory}")
    conn = setup_database(db_path)
    c = conn.cursor()

    folder_name = os.path.basename(os.path.normpath(directory)).lower()
    pattern = re.compile(r'^(?:.*?)(\d+)_(\d+)\.adt$', re.IGNORECASE)

    # Load known-good listfile
    known_good_files = set()
    if os.path.exists(listfile_path):
        with open(listfile_path, 'r', encoding='utf-8', errors='replace') as lf:
            for line in lf:
                line = line.strip()
                if line:
                    norm = normalize_filename(line)
                    if norm:
                        known_good_files.add(norm)
        logger.info(f"Loaded {len(known_good_files)} known-good filenames from {listfile_path}.")
    else:
        logger.error(f"Listfile {listfile_path} does not exist. Missing file checks will fail.")
    
    all_unique_ids = []
    missing_files_reported = set()  # to prevent duplicates

    def check_and_log_missing(fname, adt_fname):
        if known_good_files and fname and fname != "<invalid offset>":
            # Only log if truly missing after normalization
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
            c.execute("INSERT INTO adt_files (name, folder_name, x_coord, y_coord) VALUES (?,?,?,?)",
                      (filename, folder_name, x, y))
            adt_id = c.lastrowid

            # Check textures
            for tex in parsed['textures']:
                c.execute("INSERT INTO textures (adt_id, texture) VALUES (?,?)", (adt_id, tex))
                check_and_log_missing(tex, filename)

            # Check M2 models
            for mm in parsed['m2_models']:
                c.execute("INSERT INTO m2_models (adt_id, model_name) VALUES (?,?)", (adt_id, mm))
                check_and_log_missing(mm, filename)

            # Check WMO models
            for wm in parsed['wmo_models']:
                c.execute("INSERT INTO wmo_models (adt_id, wmo_name) VALUES (?,?)", (adt_id, wm))
                check_and_log_missing(wm, filename)

            # Check MDDF placements
            for m in parsed['mddf']:
                c.execute("""
                INSERT INTO mddf (adt_id, uniqueId, model_name, posX, posY, posZ, rotX, rotY, rotZ, scale, flags)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    adt_id, m['uniqueId'], m['model_name'],
                    m['position'][0], m['position'][1], m['position'][2],
                    m['rotation'][0], m['rotation'][1], m['rotation'][2],
                    m['scale'], m['flags']
                ))
                all_unique_ids.append(m['uniqueId'])
                check_and_log_missing(m['model_name'], filename)

            # Check MODF placements
            for w in parsed['modf']:
                c.execute("""
                INSERT INTO modf (adt_id, uniqueId, wmo_name, posX, posY, posZ, rotX, rotY, rotZ, scale, flags)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    adt_id, w['uniqueId'], w['wmo_name'],
                    w['position'][0], w['position'][1], w['position'][2],
                    w['rotation'][0], w['rotation'][1], w['rotation'][2],
                    w['scale'], w['flags']
                ))
                all_unique_ids.append(w['uniqueId'])
                check_and_log_missing(w['wmo_name'], filename)

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
