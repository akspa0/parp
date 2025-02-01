import os
import sqlite3
import struct
import re
import logging
from chunk_rebuilder import rebuild_chunks, write_chunk, parse_mddf, parse_modf, normalize_filename

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def read_chunk(data, pos):
    """Reads a chunk from binary data."""
    if pos + 8 > len(data):
        return None, None, None
    chunk_name = data[pos:pos+4]
    chunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]
    chunk_data = data[pos+8:pos+8+chunk_size]
    return chunk_name, chunk_data, pos+8+chunk_size

def parse_missing_log(missing_log_path):
    """Parses the missing files log to get invalid references per (x, y) coordinate."""
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

def main(db_path, adt_dir, missing_log_path):
    """Main function for patching ADT files."""
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

        # Parse placement data
        mddf_entries = parse_mddf(mddf_data_bin) if mddf_data_bin else []
        modf_entries = parse_modf(modf_data_bin) if modf_data_bin else []

        # Get original model names for remapping
        orig_m2 = m2_models
        orig_wmo = wmo_models

        # Rebuild all chunks using the chunk rebuilder module
        rebuilt_chunks = rebuild_chunks(
            valid_m2, valid_wmo, valid_textures,
            mddf_entries, modf_entries,
            orig_m2, orig_wmo
        )

        # Reconstruct the final ADT file
        out_data = b''.join(
            write_chunk(cn, cd) for cn, cd in chunks
            if cn not in rebuilt_chunks
        )
        for chunk_name, chunk_data in rebuilt_chunks.items():
            if chunk_data:
                out_data += chunk_data

        # Save the patched ADT file
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
