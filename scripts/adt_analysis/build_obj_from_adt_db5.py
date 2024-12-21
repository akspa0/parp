#!/usr/bin/env python3
"""
build_obj_from_raw_db.py

This script assumes your SQLite database ALREADY has raw (x,y,z)
coordinates for every terrain vertex. Possibly also the triangle connectivity
(each face's vertex indices). No chunk-based math, no flipping, no 145-float logic.

Example DB schema:
  CREATE TABLE terrain_vertices (
      id INTEGER PRIMARY KEY,
      x REAL,
      y REAL,
      z REAL
  );

  CREATE TABLE terrain_faces (
      id INTEGER PRIMARY KEY,
      v1 INTEGER,
      v2 INTEGER,
      v3 INTEGER
  );

If that's how your data is stored, we can just do:

  SELECT x, y, z FROM terrain_vertices ORDER BY id
  SELECT v1, v2, v3 FROM terrain_faces ORDER BY id

Then build a .OBJ with no transformations.

Usage:
  python build_obj_from_raw_db.py <db_path> <output_obj>
"""

import sys
import sqlite3

def main(db_path, output_obj):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # 1) Fetch all vertices in ID order
    #    We assume 'id' is a 1-based or 0-based sequence that will map to .OBJ index ( +1 if needed ).
    #    If it's 1-based already, that’s convenient for faces. Otherwise, we’ll offset in code.
    vertex_rows = c.execute("SELECT id, x, y, z FROM terrain_vertices ORDER BY id").fetchall()

    # We'll store them in a list, but keep track of the minimal ID in case it starts from 0 or 1.
    # If your DB always starts from 1 with no gaps, you can skip this step. We'll handle the general case.
    if not vertex_rows:
        print("No vertices found in terrain_vertices table.")
        conn.close()
        return

    min_id = min(row[0] for row in vertex_rows)
    max_id = max(row[0] for row in vertex_rows)
    print(f"Found {len(vertex_rows)} vertices, ID range [{min_id}..{max_id}].")

    # We'll store them in a dict: vertex_dict[id] = (x,y,z)
    # so we can reference them by ID when we build the faces.
    vertex_dict = {}
    for (vid, x, y, z) in vertex_rows:
        vertex_dict[vid] = (x, y, z)

    # 2) Fetch all faces
    face_rows = c.execute("SELECT id, v1, v2, v3 FROM terrain_faces ORDER BY id").fetchall()
    if not face_rows:
        print("No faces found in terrain_faces table (or no table). Writing just points.")
    else:
        print(f"Found {len(face_rows)} faces, ID range [{min(row[0] for row in face_rows)}..{max(row[0] for row in face_rows)}].")

    conn.close()

    # 3) Build .OBJ
    # We have potentially arbitrary IDs for vertices, so we'll reindex them in ascending order 
    # to produce a 1-based consecutive .OBJ index.

    # Sort vertex IDs ascending
    sorted_ids = sorted(vertex_dict.keys())
    # Map old ID -> new 1-based index
    new_index_map = {}
    for i, old_id in enumerate(sorted_ids):
        new_index_map[old_id] = i + 1  # OBJ indices are 1-based

    # We'll produce a list of (x,y,z) in new index order:
    sorted_vertices = [vertex_dict[oid] for oid in sorted_ids]

    # We also re-map face vertex IDs from (v1, v2, v3) in old ID 
    # to (new_index_map[v1], new_index_map[v2], new_index_map[v3]).
    mapped_faces = []
    for (fid, v1, v2, v3) in face_rows:
        nv1 = new_index_map[v1]
        nv2 = new_index_map[v2]
        nv3 = new_index_map[v3]
        mapped_faces.append((nv1, nv2, nv3))

    # 4) Write the OBJ
    with open(output_obj, "w") as f:
        f.write("# Raw terrain from DB, no chunk math.\n")

        # Write all vertices
        for (x, y, z) in sorted_vertices:
            f.write(f"v {x} {y} {z}\n")

        # Write all faces
        for (a, b, c) in mapped_faces:
            f.write(f"f {a} {b} {c}\n")

    print(f"Wrote .OBJ with {len(sorted_vertices)} vertices, {len(mapped_faces)} faces => {output_obj}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python build_obj_from_raw_db.py <db_path> <output_obj>")
        sys.exit(1)

    db_path = sys.argv[1]
    output_obj = sys.argv[2]
    main(db_path, output_obj)
