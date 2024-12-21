#!/usr/bin/env python3
"""
chunk_definitions.py

1) Database schemas for many ADT chunks:
   - adt_files
   - mphd, mcin
   - mcnk (header) plus sub-chunks: mcvt, mcnr, mcly, mcal
   - mddf, modf
2) Parsers for each chunk. 
"""

import sqlite3
import struct
import logging

logger = logging.getLogger(__name__)

def setup_database(db_path: str) -> sqlite3.Connection:
    """
    Creates a fresh DB with all tables needed for ADT chunk storage. 
    Force-drops each table so older leftover definitions won't conflict.
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    #
    # 1) DROP old tables
    #
    c.execute("DROP TABLE IF EXISTS mphd")
    c.execute("DROP TABLE IF EXISTS mcin")
    c.execute("DROP TABLE IF EXISTS mcnk")
    c.execute("DROP TABLE IF EXISTS mcvt")
    c.execute("DROP TABLE IF EXISTS mcnr")
    c.execute("DROP TABLE IF EXISTS mcly")
    c.execute("DROP TABLE IF EXISTS mcal")
    c.execute("DROP TABLE IF EXISTS mddf")
    c.execute("DROP TABLE IF EXISTS modf")
    c.execute("DROP TABLE IF EXISTS adt_files")

    #
    # 2) Create them fresh
    #

    # Basic ADT file references
    c.execute("""
    CREATE TABLE adt_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        folder_name TEXT,
        x_coord INTEGER,
        y_coord INTEGER
    )
    """)

    # MPHD
    c.execute("""
    CREATE TABLE mphd (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        adt_id INTEGER,
        flags INTEGER,
        something INTEGER,
        unused0 INTEGER,
        unused1 INTEGER,
        unused2 INTEGER,
        unused3 INTEGER,
        unused4 INTEGER,
        unused5 INTEGER
    )
    """)

    # MCIN
    c.execute("""
    CREATE TABLE mcin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        adt_id INTEGER,
        idx INTEGER,
        offset INTEGER,
        size INTEGER,
        flags INTEGER,
        async_id INTEGER
    )
    """)

    # MCNK header
    c.execute("""
    CREATE TABLE mcnk (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        adt_id INTEGER,
        chunk_index INTEGER,
        file_offset INTEGER,
        size INTEGER,
        flags INTEGER,
        ix INTEGER,
        iy INTEGER,
        nLayers INTEGER,
        nDoodadRefs INTEGER,
        ofsHeight INTEGER,
        ofsNormal INTEGER,
        ofsLayer INTEGER,
        ofsRefs INTEGER,
        ofsAlpha INTEGER,
        sizeAlpha INTEGER,
        ofsShadow INTEGER,
        sizeShadow INTEGER,
        areaid INTEGER,
        nMapObjRefs INTEGER,
        holes INTEGER,
        ofsSndEmitters INTEGER,
        nSndEmitters INTEGER,
        ofsLiquid INTEGER,
        sizeLiquid INTEGER,
        zpos REAL,
        xpos REAL,
        ypos REAL,
        ofsMCCV INTEGER,
        unused1 INTEGER
    )
    """)

    # MCVT: terrain heights
    c.execute("""
    CREATE TABLE mcvt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mcnk_id INTEGER,
        num_floats INTEGER,
        heights TEXT
    )
    """)

    # MCNR: vertex normals
    c.execute("""
    CREATE TABLE mcnr (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mcnk_id INTEGER,
        num_normals INTEGER,
        normals TEXT
    )
    """)

    # MCLY: texture layers
    c.execute("""
    CREATE TABLE mcly (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mcnk_id INTEGER,
        layer_index INTEGER,
        textureID INTEGER,
        flags INTEGER,
        ofsAlpha INTEGER,
        effectID INTEGER
    )
    """)

    # MCAL: alpha maps
    c.execute("""
    CREATE TABLE mcal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mcnk_id INTEGER,
        layer_index INTEGER,
        uncompressed_size INTEGER,
        alpha_data BLOB
    )
    """)

    # MDDF: doodad placements
    c.execute("""
    CREATE TABLE mddf (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        adt_id INTEGER,
        nameId INTEGER,
        uniqueId INTEGER,
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

    # MODF: WMO placements (19 columns + PK)
    c.execute("""
    CREATE TABLE modf (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        adt_id INTEGER,
        nameId INTEGER,
        uniqueId INTEGER,
        posX REAL,
        posY REAL,
        posZ REAL,
        rotX REAL,
        rotY REAL,
        rotZ REAL,
        lx REAL,
        ly REAL,
        lz REAL,
        ux REAL,
        uy REAL,
        uz REAL,
        flags INTEGER,
        doodadSet INTEGER,
        nameSet INTEGER,
        scale REAL
    )
    """)

    conn.commit()
    return conn


#
# -----------
# Chunk Parsers
# ----------- 
#

def read_reversed_chunk(data: bytes, pos: int):
    """Always reversed chunk sig for ADT."""
    chunk_sig_raw = data[pos:pos+4]
    chunk_sig = chunk_sig_raw[::-1]
    chunk_size = struct.unpack("<I", data[pos+4:pos+8])[0]
    return chunk_sig, chunk_size


def parse_mphd(data: bytes, adt_id: int, conn: sqlite3.Connection):
    """MPHD chunk: typically 32 bytes."""
    c = conn.cursor()
    if len(data) < 32:
        logger.warning("MPHD chunk too small.")
        return
    vals = struct.unpack("<2I6I", data[:32])
    flags = vals[0]
    something = vals[1]
    unused = list(vals[2:])
    c.execute("""
        INSERT INTO mphd (
            adt_id, flags, something,
            unused0, unused1, unused2, unused3, unused4, unused5
        ) VALUES (?,?,?,?,?,?,?,?)
    """, (
        adt_id,
        flags, something,
        unused[0], unused[1], unused[2],
        unused[3], unused[4], unused[5]
    ))


def parse_mcin(data: bytes, adt_id: int, conn: sqlite3.Connection):
    """MCIN: 256 entries of 16 bytes each."""
    c = conn.cursor()
    if len(data) < 4096:
        logger.warning("MCIN chunk too small.")
        return
    pos = 0
    for idx in range(256):
        offset, size_, flags_, async_id = struct.unpack("<4I", data[pos:pos+16])
        pos += 16
        c.execute("""
            INSERT INTO mcin (adt_id, idx, offset, size, flags, async_id)
            VALUES (?,?,?,?,?,?)
        """, (adt_id, idx, offset, size_, flags_, async_id))


def parse_mddf(data: bytes, adt_id: int, conn: sqlite3.Connection):
    """MDDF: Doodad placements (36 bytes each)."""
    c = conn.cursor()
    size_each = 36
    total = len(data) // size_each
    for i in range(total):
        rec = data[i*36 : (i+1)*36]
        nameId, uniqueId = struct.unpack("<II", rec[0:8])
        posX, posY, posZ = struct.unpack("<fff", rec[8:20])
        rotX, rotY, rotZ = struct.unpack("<fff", rec[20:32])
        scale, flags_ = struct.unpack("<HH", rec[32:36])
        c.execute("""
            INSERT INTO mddf (
                adt_id, nameId, uniqueId,
                posX, posY, posZ,
                rotX, rotY, rotZ,
                scale, flags
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            adt_id, nameId, uniqueId,
            posX, posY, posZ,
            rotX, rotY, rotZ,
            scale/1024.0, flags_
        ))


def parse_modf(data: bytes, adt_id: int, conn: sqlite3.Connection):
    """MODF: WMO placements (64 bytes each). 19 columns in 'modf' (excl. PK)."""
    c = conn.cursor()
    size_each = 64
    total = len(data) // size_each
    for i in range(total):
        rec = data[i*64 : (i+1)*64]
        nameId, uniqueId = struct.unpack("<II", rec[0:8])
        posX, posY, posZ = struct.unpack("<fff", rec[8:20])
        rotX, rotY, rotZ = struct.unpack("<fff", rec[20:32])
        lx, ly, lz       = struct.unpack("<fff", rec[32:44])
        ux, uy, uz       = struct.unpack("<fff", rec[44:56])
        flags_, doodadSet, nameSet, scale = struct.unpack("<HHHH", rec[56:64])
        scale_val = scale / 1024.0

        # 19 placeholders for 19 columns
        c.execute("""
            INSERT INTO modf (
                adt_id,
                nameId, uniqueId,
                posX, posY, posZ,
                rotX, rotY, rotZ,
                lx, ly, lz,
                ux, uy, uz,
                flags, doodadSet, nameSet, scale
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            adt_id,
            nameId, uniqueId,
            posX, posY, posZ,
            rotX, rotY, rotZ,
            lx, ly, lz,
            ux, uy, uz,
            flags_, doodadSet, nameSet, scale_val
        ))
    conn.commit()


#
# --- MCNK & Sub-chunks
#

def parse_mcnk(data: bytes, adt_id: int, file_offset: int, chunk_size: int, conn: sqlite3.Connection):
    """
    96-byte MCNK header + sub-chunks (MCVT, MCNR, MCLY, MCAL, etc.)
    """
    c = conn.cursor()
    if len(data) < 96:
        logger.warning("MCNK chunk too small.")
        return

    part1 = struct.unpack("<16I", data[:64])
    doodad_mapping = struct.unpack("<8H", data[64:80])
    doodad_stencil = struct.unpack("<8B", data[80:88])
    part2 = struct.unpack("<IIIIfffII", data[88:88+36])

    header = {
        "flags": part1[0],
        "ix": part1[1],
        "iy": part1[2],
        "nLayers": part1[3],
        "nDoodadRefs": part1[4],
        "ofsHeight": part1[5],
        "ofsNormal": part1[6],
        "ofsLayer": part1[7],
        "ofsRefs": part1[8],
        "ofsAlpha": part1[9],
        "sizeAlpha": part1[10],
        "ofsShadow": part1[11],
        "sizeShadow": part1[12],
        "areaid": part1[13],
        "nMapObjRefs": part1[14],
        "holes": part1[15],
        "ofsSndEmitters": part2[0],
        "nSndEmitters": part2[1],
        "ofsLiquid": part2[2],
        "sizeLiquid": part2[3],
        "zpos": part2[4],
        "xpos": part2[5],
        "ypos": part2[6],
        "ofsMCCV": part2[7],
        "unused1": part2[8],
    }

    # Insert MCNK row
    chunk_index = -1  # If you want to cross-ref MCIN offsets, do so. We'll just store -1 here.
    c.execute("""
        INSERT INTO mcnk (
            adt_id, chunk_index, file_offset, size,
            flags, ix, iy,
            nLayers, nDoodadRefs,
            ofsHeight, ofsNormal, ofsLayer, ofsRefs,
            ofsAlpha, sizeAlpha,
            ofsShadow, sizeShadow,
            areaid, nMapObjRefs, holes,
            ofsSndEmitters, nSndEmitters,
            ofsLiquid, sizeLiquid,
            zpos, xpos, ypos,
            ofsMCCV, unused1
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        adt_id, chunk_index, file_offset, chunk_size,
        header["flags"],
        header["ix"], header["iy"],
        header["nLayers"], header["nDoodadRefs"],
        header["ofsHeight"], header["ofsNormal"], header["ofsLayer"], header["ofsRefs"],
        header["ofsAlpha"], header["sizeAlpha"],
        header["ofsShadow"], header["sizeShadow"],
        header["areaid"], header["nMapObjRefs"], header["holes"],
        header["ofsSndEmitters"], header["nSndEmitters"],
        header["ofsLiquid"], header["sizeLiquid"],
        header["zpos"], header["xpos"], header["ypos"],
        header["ofsMCCV"], header["unused1"]
    ))
    mcnk_id = c.lastrowid

    # Sub-chunks
    sub_data = data[96:]
    sub_pos = 0
    sub_size = len(sub_data)

    layer_index_for_mcal = 0

    while sub_pos + 8 <= sub_size:
        sub_sig_raw = sub_data[sub_pos:sub_pos+4]
        sub_sig = sub_sig_raw[::-1]  # reversed
        sub_len = struct.unpack("<I", sub_data[sub_pos+4:sub_pos+8])[0]
        if sub_pos + 8 + sub_len > sub_size:
            logger.warning("MCNK sub-chunk extends beyond MCNK data.")
            break

        sub_payload = sub_data[sub_pos+8 : sub_pos+8+sub_len]
        sub_pos += 8 + sub_len

        if sub_sig == b'MCVT':
            parse_mcvt(sub_payload, mcnk_id, conn)
        elif sub_sig == b'MCNR':
            parse_mcnr(sub_payload, mcnk_id, conn)
        elif sub_sig == b'MCLY':
            parse_mcly(sub_payload, mcnk_id, conn)
        elif sub_sig == b'MCAL':
            parse_mcal(sub_payload, mcnk_id, layer_index_for_mcal, conn)
            layer_index_for_mcal += 1
        else:
            # e.g. MCCV, MCSH, ...
            pass

def parse_mcvt(data: bytes, mcnk_id: int, conn: sqlite3.Connection):
    """Terrain heights (145 floats typical)."""
    c = conn.cursor()
    float_count = len(data) // 4
    floats = struct.unpack("<%df" % float_count, data)
    heights_str = " ".join(str(v) for v in floats)
    c.execute("""
        INSERT INTO mcvt (mcnk_id, num_floats, heights)
        VALUES (?,?,?)
    """, (mcnk_id, float_count, heights_str))

def parse_mcnr(data: bytes, mcnk_id: int, conn: sqlite3.Connection):
    """Vertex normals (145 sets of 3 bytes)."""
    c = conn.cursor()
    if len(data) % 3 != 0:
        logger.warning("MCNR length not multiple of 3.")
    normal_count = len(data)//3
    normals = []
    pos = 0
    for _ in range(normal_count):
        x, y, z = struct.unpack("<BBB", data[pos:pos+3])
        normals.append((x, y, z))
        pos += 3
    norm_str = " ".join(f"{n[0]} {n[1]} {n[2]}" for n in normals)
    c.execute("""
        INSERT INTO mcnr (mcnk_id, num_normals, normals)
        VALUES (?,?,?)
    """, (mcnk_id, normal_count, norm_str))

def parse_mcly(data: bytes, mcnk_id: int, conn: sqlite3.Connection):
    """MCLY: up to 4 layers, each 16 bytes."""
    c = conn.cursor()
    pos = 0
    idx = 0
    while pos + 16 <= len(data):
        textureID, flags, ofsAlpha, effectID = struct.unpack("<4I", data[pos:pos+16])
        pos += 16
        c.execute("""
            INSERT INTO mcly (
                mcnk_id, layer_index, textureID, flags, ofsAlpha, effectID
            ) VALUES (?,?,?,?,?,?)
        """, (
            mcnk_id, idx, textureID, flags, ofsAlpha, effectID
        ))
        idx += 1

def parse_mcal(data: bytes, mcnk_id: int, layer_index: int, conn: sqlite3.Connection):
    """MCAL: alpha maps. We'll just store raw in 'mcal' BLOB."""
    c = conn.cursor()
    c.execute("""
        INSERT INTO mcal (mcnk_id, layer_index, uncompressed_size, alpha_data)
        VALUES (?,?,?,?)
    """, (mcnk_id, layer_index, len(data), data))

