import os
import json
import logging
import argparse
from datetime import datetime
import numpy as np
from PIL import Image

# Setup logging to file and console
log_filename = f"advanced_visualization_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler(log_filename),
    logging.StreamHandler()
])
logger = logging.getLogger()

def create_texture(light, texture_file):
    try:
        color = light["color"]
        radius = light.get("radius", 1.0)
        falloff = light.get("falloff", 1.0)

        # Create a simple texture image with the light color
        img = Image.new('RGB', (256, 256), (color[0], color[1], color[2]))

        # Save the texture image
        img.save(texture_file)
        logger.info(f"Generated texture file at {texture_file}")

    except Exception as e:
        logger.error(f"Error creating texture file: {e}")

def create_point_obj(lights, output_filename):
    try:
        obj_file = output_filename + "_points.obj"
        mtl_file = output_filename + "_points.mtl"

        with open(obj_file, 'w') as f:
            f.write(f"mtllib {os.path.basename(mtl_file)}\n")

            for i, light in enumerate(lights):
                pos = light["position"]

                f.write(f"o Light{i}\n")
                f.write(f"v {pos['x']} {pos['y']} {pos['z']}\n")
                f.write(f"usemtl Material{i}\n")

        with open(mtl_file, 'w') as f:
            for i, light in enumerate(lights):
                color = light["color"]
                texture_file = output_filename + f"_texture_{i}.png"
                create_texture(light, texture_file)

                f.write(f"newmtl Material{i}\n")
                f.write(f"map_Kd {os.path.basename(texture_file)}\n")
                f.write(f"Kd {color[0] / 255.0} {color[1] / 255.0} {color[2] / 255.0}\n")
                f.write(f"# Radius: {light.get('radius', 1.0)}\n")
                f.write(f"# Falloff: {light.get('falloff', 1.0)}\n")

        logger.info(f"Generated points OBJ file at {obj_file}")
        logger.info(f"Generated MTL file at {mtl_file}")

    except Exception as e:
        logger.error(f"Error creating points OBJ file: {e}")

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
                            create_point_obj(valid_lights, output_base)
                        logger.info(f"Processed {input_file} to {output_base}_points.obj")
                except Exception as e:
                    logger.error(f"Error processing file {input_file}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate OBJ files from JSON files containing light data.")
    parser.add_argument('input_dir', help="Directory containing JSON files")
    parser.add_argument('output_dir', help="Directory to save OBJ files")
    parser.add_argument('visualization_type', choices=['obj'], help="Type of visualization to create (obj)")

    args = parser.parse_args()

    process_json_files(args.input_dir, args.output_dir, args.visualization_type)
