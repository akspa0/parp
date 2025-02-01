import struct
import sys

def read_c_string_list(data):
    # Splits a null-terminated string block into a list of strings.
    strings = data.split(b'\0')
    return [s.decode('utf-8', 'replace') for s in strings if s]

def load_name_list(base_block, offsets):
    # Given a base block of null-terminated strings and a list of offsets, return names.
    # Offsets and strings remain little-endian as normal WoW ADTs.
    names = []
    for off in offsets:
        if off >= len(base_block):
            # Offset out of range
            names.append("<invalid offset>")
            continue
        end = base_block.find(b'\0', off)
        if end == -1:
            name = base_block[off:].decode('utf-8', 'replace')
        else:
            name = base_block[off:end].decode('utf-8', 'replace')
        names.append(name)
    return names

def parse_adt(filename):
    with open(filename, 'rb') as f:
        data = f.read()

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

        # Reverse only the chunk name bytes, keep them as ASCII
        chunk_name = data[pos:pos+4][::-1]
        chunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]
        chunk_data = data[pos+8:pos+8+chunk_size]
        pos += 8 + chunk_size

        if chunk_name == b'MVER':
            have_MVER = True
            adt_version = struct.unpack('<I', chunk_data[0:4])[0]
        elif chunk_name == b'MHDR':
            have_MHDR = True
        elif chunk_name == b'MCIN':
            have_MCIN = True
        elif chunk_name == b'MTEX':
            have_MTEX = True
            textures = read_c_string_list(chunk_data)
        elif chunk_name == b'MMDX':
            have_MMDX = True
            mmdx_block = chunk_data
        elif chunk_name == b'MMID':
            have_MMID = True
            count = len(chunk_data)//4
            mmid_offsets = list(struct.unpack('<' + 'I'*count, chunk_data))
        elif chunk_name == b'MWMO':
            mwmo_block = chunk_data
        elif chunk_name == b'MWID':
            count = len(chunk_data)//4
            mwid_offsets = list(struct.unpack('<' + 'I'*count, chunk_data))
        elif chunk_name == b'MDDF':
            # parse MDDF with little-endian
            count = len(chunk_data) // 36
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

    errors = []

    if not have_MVER:
        errors.append("Missing MVER chunk.")
    if not have_MHDR:
        errors.append("Missing MHDR chunk.")
    if not have_MCIN:
        errors.append("Missing MCIN chunk.")
    if not have_MTEX:
        errors.append("Missing MTEX chunk.")

    if adt_version is not None and adt_version != 18:
        errors.append(f"ADT version is {adt_version}, expected 18.")

    m2_names = []
    if have_MMDX and have_MMID:
        if mmid_offsets:
            m2_names = load_name_list(mmdx_block, mmid_offsets)
        else:
            errors.append("MMID offsets empty but MMDX present.")
    else:
        if m2_placements and (not have_MMDX or not have_MMID):
            errors.append("MDDF present without MMDX/MMID for M2 model names.")

    wmo_names = []
    if mwmo_block and mwid_offsets:
        wmo_names = load_name_list(mwmo_block, mwid_offsets)
    elif wmo_placements and (not mwmo_block or not mwid_offsets):
        errors.append("MODF present without MWMO/MWID for WMO model names.")

    # Verify references
    for m in m2_placements:
        if m['nameId'] >= len(m2_names):
            errors.append(f"MDDF nameId {m['nameId']} out of range.")

    for w in wmo_placements:
        if w['nameId'] >= len(wmo_names):
            errors.append(f"MODF nameId {w['nameId']} out of range.")

    # Check unique IDs in MDDF
    unique_ids = {m['uniqueId'] for m in m2_placements}
    if len(unique_ids) != len(m2_placements):
        errors.append("MDDF uniqueIds are not unique.")

    for m in m2_placements:
        model_name = m2_names[m['nameId']] if m['nameId'] < len(m2_names) else "<invalid>"
        m['model_name'] = model_name

    for w in wmo_placements:
        wmo_name = wmo_names[w['nameId']] if w['nameId'] < len(wmo_names) else "<invalid>"
        w['wmo_name'] = wmo_name

    print("Validation and Parsing Results:")
    if errors:
        print("Errors found:")
        for e in errors:
            print("  -", e)
    else:
        print("No structural errors found. File appears well-formed.")

    print("\nTextures (MTEX):")
    for t in textures:
        print("  ", t)
    print()

    print("M2 Models:")
    for i, n in enumerate(m2_names):
        print(f"  {i}: {n}")
    print()

    print("WMO Models:")
    for i, n in enumerate(wmo_names):
        print(f"  {i}: {n}")
    print()

    print("MDDF Placements:")
    for m in m2_placements:
        print(f"  uniqueId={m['uniqueId']}, model={m['model_name']}, pos={m['position']}, rot={m['rotation']}, scale={m['scale']}, flags={m['flags']}")
    print()

    print("MODF Placements:")
    for w in wmo_placements:
        print(f"  uniqueId={w['uniqueId']}, wmo={w['wmo_name']}, pos={w['position']}, rot={w['rotation']}, scale={w['scale']}, flags={w['flags']}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parse_adt.py <file.adt>")
        sys.exit(1)
    parse_adt(sys.argv[1])
