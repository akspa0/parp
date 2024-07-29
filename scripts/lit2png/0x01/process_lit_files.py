import os
import logging
import argparse
import math
from datetime import datetime
from lit_reader import read_lit_file, is_valid_light, MAX_COORD
from exporter import export_to_json, export_to_txt
from image_creator import create_image_from_lights
from obj_exporter import export_to_obj

# Setup logging to file and console
log_filename = f"process_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler(log_filename),
    logging.StreamHandler()
])
logger = logging.getLogger()

def process_lit_files(input_dir, output_dir, map_size=4096, show_radius=True, track_empty_named_lights=True, opacity=20, background_color='white', generate_3d_objects=False, max_lights=256):
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.lit'):
                input_file = os.path.join(root, file)
                relative_path = os.path.relpath(root, input_dir)
                output_json_file = os.path.join(output_dir, relative_path, f"{os.path.splitext(file)[0]}.json")
                output_image_file = os.path.join(output_dir, relative_path, f"{os.path.splitext(file)[0]}.png")
                output_txt_file = os.path.join(output_dir, relative_path, f"{os.path.splitext(file)[0]}.txt")
                output_invalid_lights_file = os.path.join(output_dir, relative_path, f"{os.path.splitext(file)[0]}_invalid.txt")
                output_invalid_lights_image = os.path.join(output_dir, relative_path, f"{os.path.splitext(file)[0]}_invalid.png")
                output_obj_file = os.path.join(output_dir, relative_path, f"{os.path.splitext(file)[0]}.obj")

                os.makedirs(os.path.dirname(output_json_file), exist_ok=True)
                os.makedirs(os.path.dirname(output_image_file), exist_ok=True)
                os.makedirs(os.path.dirname(output_txt_file), exist_ok=True)
                os.makedirs(os.path.dirname(output_invalid_lights_file), exist_ok=True)
                os.makedirs(os.path.dirname(output_invalid_lights_image), exist_ok=True)

                try:
                    data = read_lit_file(input_file, max_lights, track_empty_named_lights)
                    if data:
                        valid_lights = data["lights"]
                        invalid_lights = [light for light in data["bad_lights"] if is_valid_light(light["position"], light["color"])]

                        # Assign new names to invalid lights
                        for idx, light in enumerate(invalid_lights):
                            position = light["position"]
                            if any(math.isnan(coord) or abs(coord) > MAX_COORD for coord in position):
                                light["light_name"] = f"Invalid Light {idx+1}"
                            else:
                                light["light_name"] = f"Invalid Light {position[0]}_{position[1]}_{position[2]}"
                            # Convert position to dictionary for consistent processing
                            light["position"] = {
                                "x": light["position"][0] / 36,
                                "y": light["position"][2] / 36,
                                "z": light["position"][1] / 36
                            }

                        export_to_json(data, output_json_file)
                        export_to_txt(data, output_txt_file)
                        export_to_txt({"lights": invalid_lights, "bad_lights": []}, output_invalid_lights_file)
                        create_image_from_lights(valid_lights, output_image_file, map_size, show_radius, opacity, background_color)
                        create_image_from_lights(invalid_lights, output_invalid_lights_image, map_size, show_radius, opacity, background_color)
                        if generate_3d_objects:
                            export_to_obj(valid_lights, output_obj_file)
                        logger.info(f"Processed {input_file} to {output_json_file}, {output_image_file}, {output_txt_file}, {output_invalid_lights_file}, and {output_invalid_lights_image}")
                    else:
                        logger.warning(f"Skipped file {input_file} due to errors")
                except Exception as e:
                    logger.error(f"Error processing file {input_file}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Convert LIT files to JSON, TXT files, and PNG visualizations.")
    parser.add_argument('input_dir', help="Directory containing LIT files")
    parser.add_argument('output_dir', help="Directory to save JSON, TXT, and PNG files")
    parser.add_argument('--map_size', type=int, default=4096, help="Size of the map in pixels")
    parser.add_argument('--show_radius', action='store_true', help="Enable/disable light radius visualization")
    parser.add_argument('--track_empty_named_lights', action='store_true', default=True, help="Track lights with valid names but RGBA values of (0,0,0,0)")
    parser.add_argument('--opacity', type=int, default=20, help="Set the opacity of light color blobs (0-100)")
    parser.add_argument('--background_color', type=str, default='white', help="Background color of the image (white or black)")
    parser.add_argument('--generate_3d_objects', action='store_true', help="Generate 3D objects and textures for lights")
    parser.add_argument('--max_lights', type=int, default=256, help="Maximum number of lights to process")

    args = parser.parse_args()
    
    process_lit_files(args.input_dir, args.output_dir, args.map_size, args.show_radius, args.track_empty_named_lights, args.opacity, args.background_color, args.generate_3d_objects, args.max_lights)

if __name__ == "__main__":
    main()
