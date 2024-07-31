import os
import json
import logging
import argparse
from datetime import datetime
import numpy as np
from PIL import Image

# Constants
MAX_COORD = 17066

# Setup logging to file and console
log_filename = f"advanced_visualization_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler(log_filename),
    logging.StreamHandler()
])
logger = logging.getLogger()

def create_obj_from_lights(lights, output_filename):
    try:
        vertices = []
        colors = []

        for light in lights:
            position = light["position"]
            color = light["color"]

            vertices.append([position['x'], position['y'], position['z']])
            colors.append([color[0], color[1], color[2]])

        vertices = np.array(vertices, dtype=np.float32)
        colors = np.array(colors, dtype=np.uint8)

        obj_file = output_filename + ".obj"
        mtl_file = output_filename + ".mtl"
        texture_file = output_filename + "_texture.png"

        # Write OBJ file
        with open(obj_file, 'w') as f:
            f.write(f"mtllib {os.path.basename(mtl_file)}\n")
            for v in vertices:
                f.write(f"v {v[0]} {v[1]} {v[2]}\n")
            f.write("usemtl LightMaterial\n")
            f.write("g LightGroup\n")
            for i in range(1, len(vertices) + 1):
                f.write(f"p {i}\n")

        # Write MTL file
        with open(mtl_file, 'w') as f:
            f.write("newmtl LightMaterial\n")
            f.write(f"map_Kd {os.path.basename(texture_file)}\n")

        # Create and save texture
        texture_size = (len(colors), 1)
        texture_image = Image.fromarray(colors.reshape(texture_size + (3,)), 'RGB')
        texture_image.save(texture_file)

        logger.info(f"Generated OBJ file at {obj_file}")
        logger.info(f"Generated MTL file at {mtl_file}")
        logger.info(f"Generated texture file at {texture_file}")

    except Exception as e:
        logger.error(f"Error creating OBJ file: {e}")

def process_json_files(input_dir, output_dir, visualization_type):
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.json'):
                input_file = os.path.join(root, file)
                relative_path = os.path.relpath(root, input_dir)
                output_base = os.path.join(output_dir, relative_path, f"{os.path.splitext(file)[0]}_{visualization_type}")

                os.makedirs(os.path.dirname(output_base), exist_ok=True)

                try:
                    with open(input_file, 'r', encoding='utf-8') as json_file:
                        data = json.load(json_file)
                        valid_lights = data["lights"]
                        if visualization_type == 'obj':
                            create_obj_from_lights(valid_lights, output_base)
                        logger.info(f"Processed {input_file} to {output_base}.obj")
                except Exception as e:
                    logger.error(f"Error processing file {input_file}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate OBJ files from JSON files containing light data.")
    parser.add_argument('input_dir', help="Directory containing JSON files")
    parser.add_argument('output_dir', help="Directory to save OBJ files")
    parser.add_argument('visualization_type', choices=['obj'], help="Type of visualization to create (obj)")

    args = parser.parse_args()

    process_json_files(args.input_dir, args.output_dir, args.visualization_type)
