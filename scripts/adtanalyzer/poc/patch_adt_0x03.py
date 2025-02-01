import os
import sqlite3
import struct
import re
import logging

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def read_chunk(data, pos):
    if pos + 8 > len(data):
        return None, None, None
    chunk_name = data[pos:pos+4]
    chunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]
    chunk_data = data[pos+8:pos+8+chunk_size]
    return chunk_name, chunk_data, pos+8+chunk_size

def write_chunk(chunk_name, chunk_data):
    return chunk_name + struct.pack('<I', len(chunk_data)) + chunk_data

def normalize_filename(fname):
    if not fname or fname == "<invalid offset>":
        return ""
    fname_norm = fname.lower().replace('\\', '/')
    fname_norm = fname_norm.lstrip('./').lstrip('/')
    fname_norm = re.sub('/+', '/', fname_norm)
    if fname_norm.endswith('.mdx'):
        fname_norm = fname_norm[:-4] + '.m2'
    return fname_norm

def parse_missing_log(missing_log_path):
    missing_per_xy = {}
    if os.path.exists(missing_log_path):
        with open(missing_log_path, 'r', encoding='utf-8') as lf:
            for line in lf:
                m = re.search(r'Missing file:\s+(.*?)\s+referenced by\s+(.*\.adt)', line)
                if m:
                    missing_file = normalize_filename(m.group(1))
                    adt_ref = m.group(2)
                    coords = re.search(r'_(\d+)_(\d+)\.adt$', adt_ref)
                    if coords:
                        x, y = int(coords.group(1)), int(coords.group(2))
                        missing_per_xy.setdefault((x, y), set()).add(missing_file)
    else:
        logger.warning("Missing log file not found. Skipping missing file filtering.")
    return missing_per_xy

def parse_mddf(data):
    entries = []
    for i in range(0, len(data), 36):
        entry = struct.unpack('<IIfff' + 'fff' + 'HH', data[i:i+36])
        entries.append({
            'nameId': entry[0],
            'uniqueId': entry[1],
            'position': entry[2:5],
            'rotation': entry[5:8],
            'scale': entry[8],
            'flags': entry[9]
        })
    return entries

def parse_modf(data):
    entries = []
    for i in range(0, len(data), 64):
        entry = struct.unpack('<IIfff' + 'fff' + 'fff' + 'fff' + 'HHHH', data[i:i+64])
        entries.append({
            'nameId': entry[0],
            'uniqueId': entry[1],
            'position': entry[2:5],
            'rotation': entry[5:8],
            'extents_lower': entry[8:11],
            'extents_upper': entry[11:14],
            'flags': entry[14],
            'doodadSet': entry[15],
            'nameSet': entry[16],
            'scale': entry[17]
        })
    return entries

def build_mddf_chunk(entries):
    data = b''.join(
        struct.pack('<IIfff' + 'fff' + 'HH',
                    e['nameId'], e['uniqueId'],
                    *e['position'], *e['rotation'],
                    e['scale'], e['flags']) for e in entries
    )
    return write_chunk(b'MDDF', data)

def build_modf_chunk(entries):
    data = b''.join(
        struct.pack('<IIfff' + 'fff' + 'fff' + 'fff' + 'HHHH',
                    e['nameId'], e['uniqueId'],
                    *e['position'], *e['rotation'],
                    *e['extents_lower'], *e['extents_upper'],
                    e['flags'], e['doodadSet'], e['nameSet'], e['scale']) for e in entries
    )
    return write_chunk(b'MODF', data)

def main(db_path, adt_dir, missing_log_path):
    missing_per_xy = parse_missing_log(missing_log_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for adt_file in os.listdir(adt_dir):
        if not adt_file.endswith('.adt'):
            continue
        coords = re.search(r'_(\d+)_(\d+)\.adt$', adt_file)
        if not coords:
            logger.warning(f"Skipping {adt_file}, invalid filename format.")
            continue
        x, y = int(coords.group(1)), int(coords.group(2))
        missing_files = missing_per_xy.get((x, y), set())

        cursor.execute("SELECT id FROM adt_files WHERE x_coord=? AND y_coord=?", (x, y))
        adt_row = cursor.fetchone()
        if not adt_row:
            logger.warning(f"No database entry found for {adt_file}. Skipping.")
            continue

        adt_id = adt_row[0]
        cursor.execute("SELECT texture FROM textures WHERE adt_id=?", (adt_id,))
        textures = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT model_name FROM m2_models WHERE adt_id=?", (adt_id,))
        m2_models = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT wmo_name FROM wmo_models WHERE adt_id=?", (adt_id,))
        wmo_models = [row[0] for row in cursor.fetchall()]

        # Filter out missing files
        valid_textures = [t for t in textures if normalize_filename(t) not in missing_files]
        valid_m2 = [m for m in m2_models if normalize_filename(m) not in missing_files]
        valid_wmo = [w for w in wmo_models if normalize_filename(w) not in missing_files]

        logger.info(f"Valid textures: {len(valid_textures)}, M2 models: {len(valid_m2)}, WMO models: {len(valid_wmo)}")

        # Patch ADT file
        adt_path = os.path.join(adt_dir, adt_file)
        with open(adt_path, 'rb') as f:
            original_data = f.read()

        chunks = []
        pos = 0
        while pos < len(original_data):
            chunk_name, chunk_data, pos = read_chunk(original_data, pos)
            if chunk_name:
                chunks.append((chunk_name, chunk_data))

        # Extract specific chunk data
        mddf_data_bin = next((cd for cn, cd in chunks if cn == b'MDDF'), None)
        modf_data_bin = next((cd for cn, cd in chunks if cn == b'MODF'), None)

        # Parse and filter placements
        mddf_entries = parse_mddf(mddf_data_bin) if mddf_data_bin else []
        modf_entries = parse_modf(modf_data_bin) if modf_data_bin else []

        # Normalize filenames for filtering
        valid_m2_norm = [normalize_filename(m) for m in valid_m2]
        valid_wmo_norm = [normalize_filename(w) for w in valid_wmo]

        new_mddf_entries = [
            e for e in mddf_entries
            if e['nameId'] < len(m2_models) and normalize_filename(m2_models[e['nameId']]) in valid_m2_norm
        ]

        new_modf_entries = [
            e for e in modf_entries
            if e['nameId'] < len(wmo_models) and normalize_filename(wmo_models[e['nameId']]) in valid_wmo_norm
        ]

        # Rebuild chunks
        out_data = b''.join(
            write_chunk(cn, cd) for cn, cd in chunks
            if cn not in {b'MTEX', b'MMDX', b'MMID', b'MWMO', b'MWID', b'MDDF', b'MODF'}
        )
        out_data += build_mddf_chunk(new_mddf_entries)
        out_data += build_modf_chunk(new_modf_entries)

        output_path = os.path.join(adt_dir, adt_file.replace('.adt', '_patched.adt'))
        with open(output_path, 'wb') as f:
            f.write(out_data)
        logger.info(f"Patched ADT written to {output_path}")

    conn.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("Usage: python patch_adt.py <db_path> <adt_dir> <missing_log_path>")
        sys.exit(1)

    db_path, adt_dir, missing_log_path = sys.argv[1], sys.argv[2], sys.argv[3]
    main(db_path, adt_dir, missing_log_path)
