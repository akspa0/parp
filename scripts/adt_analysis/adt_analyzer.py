#!/usr/bin/env python3
"""
bulk_adt_analyzer_7x08.py

Main script that:
1) Creates a fresh DB with timestamp (never reusing old file).
2) For each ADT, reads reversed chunk signatures (MVER, MHDR, MCIN, MPHD, MDDF, MODF, MCNK, etc.)
3) Calls the parse_* functions from chunk_definitions to store them all in the DB.

Usage:
  python bulk_adt_analyzer_7x08.py <adt_directory>
"""

import os
import re
import sys
import struct
import logging
from datetime import datetime
import sqlite3

from chunk_definitions import (
    setup_database,
    read_reversed_chunk,
    parse_mphd,
    parse_mcin,
    parse_mcnk,
    parse_mddf,
    parse_modf
)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
db_filename = f"analysis_{timestamp}.db"

logging.basicConfig(
    filename=f"adt_parser_{timestamp}.log",
    filemode='w',
    format='%(asctime)s [%(levelname)s] %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)


def parse_adt_file(filepath: str, conn: sqlite3.Connection):
    c = conn.cursor()
    base_name = os.path.basename(filepath)
    folder_name = os.path.basename(os.path.dirname(filepath)).lower()

    # Insert file record
    x_coord, y_coord = None, None
    pat = re.compile(r'(\d+)_(\d+)\.adt$', re.IGNORECASE)
    m = pat.search(base_name)
    if m:
        x_coord = int(m.group(1))
        y_coord = int(m.group(2))

    c.execute("""
        INSERT INTO adt_files (name, folder_name, x_coord, y_coord)
        VALUES (?,?,?,?)
    """, (base_name, folder_name, x_coord, y_coord))
    adt_id = c.lastrowid

    with open(filepath, "rb") as f:
        data = f.read()

    size = len(data)
    pos = 0
    while pos + 8 <= size:
        chunk_sig, chunk_sz = read_reversed_chunk(data, pos)
        if pos + 8 + chunk_sz > size:
            logger.warning(f"{base_name}: chunk {chunk_sig} extends beyond file size.")
            break

        chunk_data = data[pos+8 : pos+8+chunk_sz]

        if chunk_sig == b'MPHD' or chunk_sig == b'MPHF':
            parse_mphd(chunk_data, adt_id, conn)
        elif chunk_sig == b'MCIN':
            parse_mcin(chunk_data, adt_id, conn)
        elif chunk_sig == b'MCNK':
            parse_mcnk(chunk_data, adt_id, pos, chunk_sz, conn)
        elif chunk_sig == b'MDDF':
            parse_mddf(chunk_data, adt_id, conn)
        elif chunk_sig == b'MODF':
            parse_modf(chunk_data, adt_id, conn)
        else:
            # MVER, MHDR, MMDX, MWMO, etc. can be handled similarly if desired
            pass

        pos += 8 + chunk_sz

    conn.commit()
    logger.info(f"Parsed {base_name}, adt_id={adt_id}")

def main(directory: str):
    logger.info(f"Starting parse in {directory}, DB => {db_filename}")
    conn = setup_database(db_filename)

    for fname in os.listdir(directory):
        if not fname.lower().endswith(".adt"):
            continue
        filepath = os.path.join(directory, fname)
        logger.info(f"Parsing {filepath}")
        parse_adt_file(filepath, conn)

    conn.close()
    logger.info(f"All done. Wrote to {db_filename}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python bulk_adt_analyzer_7x08.py <directory_of_adts>")
        sys.exit(1)
    directory = sys.argv[1]
    main(directory)
