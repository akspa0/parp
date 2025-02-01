import os
import sys
import sqlite3
import struct
import re
import logging
from datetime import datetime

logging.basicConfig(
    stream=sys.stdout,
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

def build_string_block(strings):
    return b'\0'.join(s.encode('utf-8') for s in strings) + b'\0' if strings else b''

def build_offsets_block(strings_block, strings_list):
    offsets = []
    for s in strings_list:
        off = strings_block.find((s+'\0').encode('utf-8'))
        offsets.append(off)
    return struct.pack('<' + 'I'*len(offsets), *offsets) if offsets else b''

def parse_m2_wmo_lists(mmdx_data, mmid_data, mwmo_data, mwid_data):
    m2_names = []
    wmo_names = []
    if mmdx_data and mmid_data:
        mmid_offsets = struct.unpack('<' + 'I'*(len(mmid_data)//4), mmid_data)
        for off in mmid_offsets:
            end = mmdx_data.find(b'\0', off)
            name = (mmdx_data[off:end] if end!=-1 else mmdx_data[off:]).decode('utf-8','replace')
            m2_names.append(name)
    if mwmo_data and mwid_data:
        mwid_offsets = struct.unpack('<'+'I'*(len(mwid_data)//4), mwid_data)
        for off in mwid_offsets:
            end = mwmo_data.find(b'\0', off)
            name = (mwmo_data[off:end] if end!=-1 else mwmo_data[off:]).decode('utf-8','replace')
            wmo_names.append(name)
    return m2_names, wmo_names

def normalize_filename(fname):
    if not fname or fname == "<invalid offset>":
        return ""
    fname_norm = fname.lower().replace('\\', '/')
    fname_norm = fname_norm.lstrip('./').lstrip('/')
    fname_norm = re.sub('/+', '/', fname_norm)
    if fname_norm.endswith('.mdx'):
        fname_norm = fname_norm[:-4] + '.m2'
    return fname_norm

def parse_adt_coords(filename):
    # Extract X, Y from something like parp_ek2002_X_Y.adt
    m = re.match(r'^.*_(\d+)_(\d+)\.adt$', filename, re.IGNORECASE)
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2))

def parse_missing_log(missing_log_path):
    missing_per_xy = {}
    if os.path.exists(missing_log_path):
        with open(missing_log_path, 'r', encoding='utf-8', errors='replace') as lf:
            for line in lf:
                line=line.strip()
                m = re.match(r'Missing file:\s+(.*?)\s+referenced by\s+(.*\.adt)', line, re.IGNORECASE)
                if m:
                    missing_file = normalize_filename(m.group(1))
                    adt_ref = m.group(2)
                    x,y = parse_adt_coords(os.path.basename(adt_ref))
                    if x is not None and y is not None:
                        if (x,y) not in missing_per_xy:
                            missing_per_xy[(x,y)] = set()
                        if missing_file:
                            missing_per_xy[(x,y)].add(missing_file)
    else:
        logger.warning("Missing files log not found. No missing files will be removed.")
    return missing_per_xy

def parse_mddf(data):
    # MDDF entry: 36 bytes
    # nameId(uint32), uniqueId(uint32), pos(float*3), rot(float*3), scale(uint16), flags(uint16)
    entries = []
    count = len(data)//36
    for i in range(count):
        entry = data[i*36:(i+1)*36]
        nameId, uniqueId = struct.unpack('<II', entry[0:8])
        posx, posy, posz = struct.unpack('<fff', entry[8:20])
        rotx, roty, rotz = struct.unpack('<fff', entry[20:32])
        scale, flags = struct.unpack('<HH', entry[32:36])
        entries.append({
            'nameId': nameId,
            'uniqueId': uniqueId,
            'pos': (posx, posy, posz),
            'rot': (rotx, roty, rotz),
            'scale': scale,
            'flags': flags
        })
    return entries

def parse_modf(data):
    # MODF entry: 64 bytes
    # nameId(uint32), uniqueId(uint32), pos(float*3), rot(float*3), extents_lower(float*3), extents_upper(float*3), flags(uint16), doodadSet(uint16), nameSet(uint16), scale(uint16)
    entries = []
    count = len(data)//64
    for i in range(count):
        entry = data[i*64:(i+1)*64]
        (nameId, uniqueId) = struct.unpack('<II', entry[0:8])
        posx, posy, posz = struct.unpack('<fff', entry[8:20])
        rotx, roty, rotz = struct.unpack('<fff', entry[20:32])
        lx, ly, lz = struct.unpack('<fff', entry[32:44])
        ux, uy, uz = struct.unpack('<fff', entry[44:56])
        flags, doodadSet, nameSet, scale = struct.unpack('<HHHH', entry[56:64])
        entries.append({
            'nameId': nameId,
            'uniqueId': uniqueId,
            'pos': (posx, posy, posz),
            'rot': (rotx, roty, rotz),
            'extents_lower': (lx, ly, lz),
            'extents_upper': (ux, uy, uz),
            'flags': flags,
            'doodadSet': doodadSet,
            'nameSet': nameSet,
            'scale': scale
        })
    return entries

def build_mddf_chunk(m2_placements):
    if not m2_placements:
        return b''
    data = b''
    for p in m2_placements:
        data += struct.pack('<IIfff'+'fff'+'HH',
                            p['nameId'], p['uniqueId'],
                            p['pos'][0], p['pos'][1], p['pos'][2],
                            p['rot'][0], p['rot'][1], p['rot'][2],
                            p['scale'], p['flags'])
    return write_chunk(b'MDDF', data)

def build_modf_chunk(wmo_placements):
    if not wmo_placements:
        return b''
    data = b''
    for p in wmo_placements:
        data += struct.pack('<IIfff'+'fff'+'fff'+'fff'+'HHHH',
                            p['nameId'], p['uniqueId'],
                            p['pos'][0], p['pos'][1], p['pos'][2],
                            p['rot'][0], p['rot'][1], p['rot'][2],
                            p['extents_lower'][0], p['extents_lower'][1], p['extents_lower'][2],
                            p['extents_upper'][0], p['extents_upper'][1], p['extents_upper'][2],
                            p['flags'], p['doodadSet'], p['nameSet'], p['scale'])
    return write_chunk(b'MODF', data)

def build_mmdx_mmid_chunks(final_m2):
    if not final_m2:
        return b'', b''
    mmdx_block = build_string_block(final_m2)
    mmid_data = build_offsets_block(mmdx_block, final_m2)
    return write_chunk(b'MMDX', mmdx_block), write_chunk(b'MMID', mmid_data)

def build_mwmo_mwid_chunks(final_wmo):
    if not final_wmo:
        return b'', b''
    mwmo_block = build_string_block(final_wmo)
    mwid_data = build_offsets_block(mwmo_block, final_wmo)
    return write_chunk(b'MWMO', mwmo_block), write_chunk(b'MWID', mwid_data)

def build_mtex_chunk(keep_textures):
    if not keep_textures:
        return b''
    mtex_block = build_string_block(keep_textures)
    return write_chunk(b'MTEX', mtex_block)

def main(db_path, directory, missing_log_path):
    # Load missing files keyed by (x,y)
    missing_per_xy = parse_missing_log(missing_log_path)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    for filename in os.listdir(directory):
        if not filename.lower().endswith(".adt"):
            continue
        x, y = parse_adt_coords(filename)
        if x is None or y is None:
            logger.info(f"Skipping {filename}, cannot determine X,Y coords.")
            continue

        adt_path = os.path.join(directory, filename)
        if not os.path.exists(adt_path):
            logger.info(f"ADT {filename} not found, skipping...")
            continue

        # Find matching ADT in DB by x,y
        c.execute("SELECT id FROM adt_files WHERE x_coord=? AND y_coord=?", (x, y))
        row = c.fetchone()
        if not row:
            logger.info(f"No ADT record found in DB for {filename} (x={x},y={y}), skipping...")
            continue
        adt_id = row[0]

        # Load textures, M2, WMO from DB
        c.execute("SELECT texture FROM textures WHERE adt_id=?", (adt_id,))
        textures = [r[0] for r in c.fetchall()]

        c.execute("SELECT model_name FROM m2_models WHERE adt_id=?", (adt_id,))
        m2_models = [r[0] for r in c.fetchall()]

        c.execute("SELECT wmo_name FROM wmo_models WHERE adt_id=?", (adt_id,))
        wmo_models = [r[0] for r in c.fetchall()]

        adt_missing = missing_per_xy.get((x,y), set())

        keep_textures = [t for t in textures if normalize_filename(t) not in adt_missing]
        keep_m2 = [m for m in m2_models if normalize_filename(m) not in adt_missing]
        keep_wmo = [w for w in wmo_models if normalize_filename(w) not in adt_missing]

        with open(adt_path, 'rb') as f:
            original_data = f.read()

        pos = 0
        original_chunks = []
        while True:
            cn, cd, newpos = read_chunk(original_data, pos)
            if cn is None:
                break
            original_chunks.append((cn, cd))
            pos = newpos

        # Extract original references
        mmdx_data = mmid_data = mwmo_data = mwid_data = None
        mddf_data_bin = modf_data_bin = mtex_data = None

        for (cn, cd) in original_chunks:
            if cn == b'MMDX':
                mmdx_data = cd
            elif cn == b'MMID':
                mmid_data = cd
            elif cn == b'MWMO':
                mwmo_data = cd
            elif cn == b'MWID':
                mwid_data = cd
            elif cn == b'MDDF':
                mddf_data_bin = cd
            elif cn == b'MODF':
                modf_data_bin = cd
            elif cn == b'MTEX':
                mtex_data = cd

        orig_m2_names, orig_wmo_names = parse_m2_wmo_lists(mmdx_data, mmid_data, mwmo_data, mwid_data)

        # Create normalized sets for quick lookup
        keep_m2_norm = [normalize_filename(x) for x in keep_m2]
        keep_wmo_norm = [normalize_filename(x) for x in keep_wmo]

        # Parse original placements
        m2_placements = parse_mddf(mddf_data_bin) if mddf_data_bin else []
        wmo_placements = parse_modf(modf_data_bin) if modf_data_bin else []

        # Filter placements based on missing files
        new_m2_placements = []
        for p in m2_placements:
            if p['nameId'] < len(orig_m2_names):
                model = orig_m2_names[p['nameId']]
                if normalize_filename(model) in keep_m2_norm:
                    new_m2_placements.append(p)

        new_wmo_placements = []
        for p in wmo_placements:
            if p['nameId'] < len(orig_wmo_names):
                wmoname = orig_wmo_names[p['nameId']]
                if normalize_filename(wmoname) in keep_wmo_norm:
                    new_wmo_placements.append(p)

        # Rebuild final chunks
        # Final M2/WMO lists (to remove unused entries)
        # Filter orig_m2_names, orig_wmo_names by what's actually referenced now
        used_m2_ids = {pp['nameId'] for pp in new_m2_placements}
        used_wmo_ids = {pp['nameId'] for pp in new_wmo_placements}

        final_m2_list = [nm for i,nm in enumerate(orig_m2_names) if i in used_m2_ids]
        final_wmo_list = [nm for i,nm in enumerate(orig_wmo_names) if i in used_wmo_ids]

        # Remap nameIds
        m2_name_map = {normalize_filename(nm): i for i,nm in enumerate(final_m2_list)}
        for p in new_m2_placements:
            old_name = orig_m2_names[p['nameId']]
            p['nameId'] = m2_name_map[normalize_filename(old_name)]

        wmo_name_map = {normalize_filename(nm): i for i,nm in enumerate(final_wmo_list)}
        for p in new_wmo_placements:
            old_name = orig_wmo_names[p['nameId']]
            p['nameId'] = wmo_name_map[normalize_filename(old_name)]

        new_mmdx, new_mmid = build_mmdx_mmid_chunks(final_m2_list) if final_m2_list else (b'', b'')
        new_mwmo, new_mwid = build_mwmo_mwid_chunks(final_wmo_list) if final_wmo_list else (b'', b'')
        new_mddf = build_mddf_chunk(new_m2_placements)
        new_modf = build_modf_chunk(new_wmo_placements)
        new_mtex = build_mtex_chunk(keep_textures) if keep_textures else b''

        replaced_names = {b'MMDX', b'MMID', b'MWMO', b'MWID', b'MDDF', b'MODF', b'MTEX'}

        new_chunks_map = {}
        if new_mmdx: new_chunks_map[b'MMDX'] = new_mmdx
        if new_mmid: new_chunks_map[b'MMID'] = new_mmid
        if new_mwmo: new_chunks_map[b'MWMO'] = new_mwmo
        if new_mwid: new_chunks_map[b'MWID'] = new_mwid
        if new_mtex: new_chunks_map[b'MTEX'] = new_mtex
        if new_mddf: new_chunks_map[b'MDDF'] = new_mddf
        if new_modf: new_chunks_map[b'MODF'] = new_modf

        out_data = b''
        for (cn, cd) in original_chunks:
            if cn in replaced_names:
                if cn in new_chunks_map:
                    out_data += new_chunks_map[cn]
                else:
                    # omit if no replacement
                    pass
            else:
                out_data += write_chunk(cn, cd)

        patched_path = os.path.join(directory, filename.replace('.adt', '_patched.adt'))
        with open(patched_path, 'wb') as f:
            f.write(out_data)
        logger.info(f"Patched ADT written to {patched_path}")

    conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python patch_adt.py <analysis_db_path> <directory_of_parp_adt> <missing_files_log>")
        sys.exit(1)

    db_path = sys.argv[1]
    directory = sys.argv[2]
    missing_log_path = sys.argv[3]
    main(db_path, directory, missing_log_path)
