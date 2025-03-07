import json
import sys
import os
from pathlib import Path

def convert_json_to_obj(input_file, output_file):
    print(f"Starting conversion of {input_file} to {output_file}")
    
    try:
        # Read JSON file
        with open(input_file, 'r') as f:
            print(f"Reading JSON file: {input_file}")
            data = json.load(f)

        # Extract relevant data
        print("Extracting data from JSON")
        
        # Check if VertexPositions is a list or a dictionary
        vertex_positions = data.get('VertexPositions')
        if isinstance(vertex_positions, dict):
            vertices = vertex_positions.get('Vertices', [])
        elif isinstance(vertex_positions, list):
            vertices = vertex_positions
        else:
            vertices = []

        # Check if NormalCoordinates is a list or a dictionary
        normal_coordinates = data.get('NormalCoordinates')
        if isinstance(normal_coordinates, dict):
            normals = normal_coordinates.get('Normals', [])
        elif isinstance(normal_coordinates, list):
            normals = normal_coordinates
        else:
            normals = []

        # Check if VertexIndices is a list or a dictionary
        vertex_indices = data.get('VertexIndices')
        if isinstance(vertex_indices, dict):
            indices = vertex_indices.get('Indices', [])
        elif isinstance(vertex_indices, list):
            indices = vertex_indices
        else:
            indices = []

        print(f"Found {len(vertices)} vertices, {len(normals)} normals, and {len(indices)} indices")

        # Write OBJ file
        with open(output_file, 'w') as f:
            print(f"Writing OBJ file: {output_file}")
            
            # Write vertices
            for v in vertices:
                f.write(f"v {v['X']} {v['Y']} {v['Z']}\n")

            # Write normals
            for n in normals:
                f.write(f"vn {n['X']} {n['Y']} {n['Z']}\n")

            # Write faces
            for i in range(0, len(indices), 3):
                # Check if there are enough indices for a face
                if i + 2 >= len(indices):
                    print(f"Warning: Skipping incomplete face at index {i}")
                    break

                # OBJ indices are 1-based
                v1, v2, v3 = indices[i] + 1, indices[i+1] + 1, indices[i+2] + 1
                f.write(f"f {v1}//{v1} {v2}//{v2} {v3}//{v3}\n")

        print(f"Conversion complete. OBJ file saved as {output_file}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON file: {e}")
    except KeyError as e:
        print(f"Error: Missing key in JSON data: {e}")
    except IOError as e:
        print(f"Error reading/writing file: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python json_to_obj_converter.py <input_json_file> [output_obj_file]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else Path(input_file).with_suffix('.obj')

    # Ensure input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' does not exist.")
        sys.exit(1)

    convert_json_to_obj(input_file, output_file)