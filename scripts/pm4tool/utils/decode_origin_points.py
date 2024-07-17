import sqlite3
import os
import json
import logging

def ensure_folder_exists(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)

def fetch_lrpm_data(cursor):
    query = "SELECT file_name, record_index, field_name, field_value FROM chunk_fields WHERE chunk_id = 'LRPM'"
    cursor.execute(query)
    return cursor.fetchall()

def parse_field_value(field_value):
    try:
        return json.loads(field_value)
    except json.JSONDecodeError:
        return None

def generate_obj(vertices, obj_path):
    with open(obj_path, 'w') as obj_file:
        obj_file.write("# OBJ file\n")
        for vertex in vertices:
            obj_file.write(f"v {vertex['x']} {vertex['y']} {vertex['z']}\n")
        obj_file.write("\n")

def main(db_path, output_dir):
    logging.basicConfig(level=logging.DEBUG)
    ensure_folder_exists(output_dir)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    lrpm_data = fetch_lrpm_data(cursor)
    models = {}

    for row in lrpm_data:
        file_name, record_index, field_name, field_value = row
        field_data = parse_field_value(field_value)
        
        if not field_data:
            logging.debug(f"Skipping row with invalid field data: {row}")
            continue
        
        if field_name == '_0x00':
            model_id = field_data
            if model_id not in models:
                models[model_id] = []
            logging.debug(f"Model ID: {model_id}")
        elif field_name == 'position':
            position = field_data
            if model_id:
                models[model_id].append(position)
                logging.debug(f"Added position {position} to model ID {model_id}")

    # Generate individual OBJ files
    for model_id, vertices in models.items():
        obj_path = os.path.join(output_dir, f"model_{model_id}.obj")
        generate_obj(vertices, obj_path)
        logging.debug(f"Generated OBJ for model ID {model_id} with {len(vertices)} vertices")

    # Generate combined OBJ file
    combined_obj_path = os.path.join(output_dir, "combined.obj")
    combined_vertices = []
    for vertices in models.values():
        combined_vertices.extend(vertices)
    generate_obj(combined_vertices, combined_obj_path)
    logging.debug(f"Generated combined OBJ with {len(combined_vertices)} vertices")

    conn.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate 3D OBJ files from LRPM chunk data in SQLite database.")
    parser.add_argument("db_path", type=str, help="Path to the SQLite database.")
    parser.add_argument("output_dir", type=str, help="Directory to save the OBJ files.")
    args = parser.parse_args()

    main(args.db_path, args.output_dir)
