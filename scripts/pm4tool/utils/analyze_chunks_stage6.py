import sqlite3
import json
import argparse
import logging
import os
from collections import defaultdict
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from datetime import datetime

def ensure_folder_exists(folder_path):
    if folder_path and not os.path.exists(folder_path):
        os.makedirs(folder_path)

def load_data(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = "SELECT chunk_id, field_name, field_value FROM chunk_fields"
    cursor.execute(query)
    rows = cursor.fetchall()

    conn.close()
    return rows

def analyze_field_values(data):
    analysis = defaultdict(lambda: defaultdict(list))

    for chunk_id, field_name, field_value in data:
        value = json.loads(field_value)
        analysis[chunk_id][field_name].append(value)

    analysis_results = {}
    for chunk_id, fields in analysis.items():
        analysis_results[chunk_id] = {}
        for field_name, value_list in fields.items():
            try:
                if all(isinstance(v, (int, float)) for v in value_list):
                    analysis_results[chunk_id][field_name] = {
                        "min": min(value_list),
                        "max": max(value_list),
                        "unique_values": len(set(value_list)),
                        "sample_values": value_list[:5]
                    }
                else:
                    analysis_results[chunk_id][field_name] = {
                        "unique_values": len(set(str(v) for v in value_list)),
                        "sample_values": value_list[:5]
                    }
            except TypeError as e:
                logging.error(f"Type error in field {field_name} of chunk {chunk_id}: {e}")

    return analysis_results

def save_analysis_results(results, output_file):
    ensure_folder_exists(os.path.dirname(output_file))
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4)

def save_parsed_data(vertices, indices, errors, output_dir):
    ensure_folder_exists(output_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save vertices and indices
    parsed_data = {
        "vertices": vertices,
        "indices": indices
    }
    parsed_output_file = os.path.join(output_dir, f"parsed_data_{timestamp}.json")
    with open(parsed_output_file, 'w', encoding='utf-8') as f:
        json.dump(parsed_data, f, indent=4)

    # Save errors
    error_output_file = os.path.join(output_dir, f"errors_{timestamp}.json")
    with open(error_output_file, 'w', encoding='utf-8') as f:
        json.dump(errors, f, indent=4)

def visualize_3d_model(vertices, indices, output_dir):
    ensure_folder_exists(output_dir)
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    for i in range(0, len(indices), 3):
        try:
            v0 = vertices[indices[i]]
            v1 = vertices[indices[i + 1]]
            v2 = vertices[indices[i + 2]]

            if isinstance(v0, dict) and isinstance(v1, dict) and isinstance(v2, dict):
                ax.plot([v0['x'], v1['x']], [v0['y'], v1['y']], [v0['z'], v1['z']], color='b')
                ax.plot([v1['x'], v2['x']], [v1['y'], v2['y']], [v1['z'], v2['z']], color='b')
                ax.plot([v2['x'], v0['x']], [v2['y'], v0['y']], [v2['z'], v0['z']], color='b')
            else:
                logging.error(f"Vertex data is not in the expected format: {v0}, {v1}, {v2}")
        except IndexError as e:
            logging.error(f"IndexError: {e} with indices {indices[i:i+3]} and total vertices {len(vertices)}")
        except TypeError as e:
            logging.error(f"TypeError: {e} with vertex data")

    plt.show()

def parse_vertex_data(data):
    vertices = []
    indices = []
    errors = []

    for chunk_id, fields in data.items():
        if chunk_id in ["VPSM", "TVSM", "NCSM"]:
            if all(k in fields for k in ("x", "y", "z")):
                x_values = fields["x"]["sample_values"]
                y_values = fields["y"]["sample_values"]
                z_values = fields["z"]["sample_values"]

                for x, y, z in zip(x_values, y_values, z_values):
                    if isinstance(x, (int, float)) and isinstance(y, (int, float)) and isinstance(z, (int, float)):
                        vertices.append({"x": x, "y": y, "z": z})
                    else:
                        errors.append({"chunk_id": chunk_id, "x": x, "y": y, "z": z})
        if chunk_id in ["IPSM", "MSPI", "IVSM"]:
            if "int_value" in fields:
                indices.extend(fields["int_value"]["sample_values"])

    return vertices, indices, errors

def main():
    parser = argparse.ArgumentParser(description="Analyze chunk data from SQLite database.")
    parser.add_argument("db_file", type=str, help="Path to the SQLite database file.")
    parser.add_argument("output_file", type=str, help="Path to the output JSON file.")
    args = parser.parse_args()

    data = load_data(args.db_file)
    analysis_results = analyze_field_values(data)
    
    vertices, indices, errors = parse_vertex_data(analysis_results)

    # Visualize 3D model
    try:
        visualize_3d_model(vertices, indices, os.path.dirname(args.output_file))
    except Exception as e:
        logging.error(f"Error visualizing 3D model: {e}")

    # Append a timestamp to the output filename to avoid permission issues
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file_with_timestamp = f"{os.path.splitext(args.output_file)[0]}_{timestamp}.json"
    save_analysis_results(analysis_results, output_file_with_timestamp)

    # Save parsed data and errors
    save_parsed_data(vertices, indices, errors, os.path.dirname(args.output_file))

if __name__ == "__main__":
    main()
