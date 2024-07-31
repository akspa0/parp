import os
import struct
import math
import logging
import json
import re
import argparse
from datetime import datetime
import subprocess

# Constants
MAX_COORD = 17066
MIN_TEXT_SIZE = 16  # Minimum text size in points

# Setup logging to file and console
log_filename = f"process_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler(log_filename),
    logging.StreamHandler()
])
logger = logging.getLogger()

# Exporter functions
def export_to_json(data, output_filename):
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    try:
        with open(output_filename, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, indent=4)
    except Exception as e:
        logger.error(f"Error writing JSON file {output_filename}: {e}")

def export_to_txt(data, output_filename):
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    try:
        with open(output_filename, 'w', encoding='utf-8') as txt_file:
            txt_file.write("Name,Position X,Position Y,Position Z,Color RGBA,Light Radius,Light Dropoff\n")
            for light in data["lights"]:
                try:
                    position = light["position"]
                    color = light["color"]
                    light_name = re.sub(r'[^\x00-\x7F]+', '', light['light_name'])
                    if light_name and light_name.strip('-'):
                        logger.debug(f"Writing light: {light_name} at position: {position}")
                        txt_file.write(f"{light_name},{position['x']},{position['y']},{position['z']},{color[0]},{color[1]},{color[2]},{color[3]},{light['light_radius']},{light['light_dropoff']}\n")
                    else:
                        logger.debug(f"Skipped invalid light with name: {light_name} and position: {position}")
                except KeyError as e:
                    logger.error(f"Error writing light: {light} (KeyError: {e})")
    except Exception as e:
        logger.error(f"Error writing TXT file {output_filename}: {e} ({type(e).__name__})")

def export_to_obj(lights, output_filename):
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    try:
        with open(output_filename, 'w') as obj_file:
            obj_file.write("# OBJ file\n")
            for light in lights:
                position = light["position"]
                light_radius = light["light_radius"]
                color = light["color"]
                light_name = re.sub(r'[^\x00-\x7F]+', '', light['light_name'])
                if light_name and light_name.strip('-'):
                    obj_file.write(f"v {position['x']} {position['z']} {position['y']} {color[0] / 255} {color[1] / 255} {color[2] / 255}\n")
                    obj_file.write(f"# light_radius {light_radius}\n")
                    obj_file.write(f"# light_dropoff {light['light_dropoff']}\n")
                else:
                    logger.debug(f"Skipped invalid light with name: {light_name} and position: {position}")
        logger.info(f"Exported {len(lights)} lights to {output_filename}")
    except Exception as e:
        logger.error(f"Error writing OBJ file {output_filename}: {e}")

# LIT reader functions
def is_valid_light(position, color):
    return any(coord != 0 for coord in position) or any(c != 0 for c in color)

def is_valid_name(name):
    return re.match(r'^[\w\s\-\.,]+$', name) is not None

def has_valid_coordinates(position):
    return all(len(str(abs(coord)).split('.')[-1]) <= 12 for coord in position)

def analyze_unknown_data(unknown_data):
    # Analyze the unknown data chunk here
    # This is a placeholder function, implement the actual analysis logic as needed
    logger.info(f"Analyzing unknown data: {unknown_data}")

def read_lit_file(file_path, max_lights, track_empty_named_lights=True):
    unknown_data_chunks = []
    try:
        with open(file_path, 'rb') as file:
            header = file.read(4)
            version = struct.unpack('B', header[0:1])[0]
            logger.debug(f"Version: {version}")
            
            if version == 2:
                file_format = 'old'
                header_size = 4  # Old format has a 4-byte header
                file.seek(0)  # Reset to start
            else:
                file_format = 'new'
                header_size = 8
            
            entry_size = 60 if file_format == 'old' else 64
            
            if file_format == 'new':
                file.seek(0)
                header = file.read(header_size)
                version = struct.unpack('B', header[0:1])[0]
                reported_light_count = struct.unpack('I', header[4:8])[0]
            else:
                file.seek(0)
                header = file.read(header_size)
                version = struct.unpack('B', header[0:1])[0]
                reported_light_count = -1
            
            file_size = os.path.getsize(file_path)
            actual_light_count = min((file_size - header_size) // entry_size, max_lights)
            
            logger.debug(f"File format: {file_format}")
            logger.debug(f"Reported Light Count: {reported_light_count}")
            logger.debug(f"Calculated Actual Light Count: {actual_light_count}")
            
            lights = []
            for i in range(actual_light_count):
                light_data = file.read(entry_size)
                try:
                    if file_format == 'new':
                        chunk = struct.unpack('2i', light_data[0:8])
                        chunk_radius = struct.unpack('i', light_data[8:12])[0]
                        position = struct.unpack('3f', light_data[12:24])
                        light_radius = struct.unpack('f', light_data[24:28])[0] / 36
                        light_dropoff = struct.unpack('f', light_data[28:32])[0] / 36
                        light_name = light_data[32:64].decode('utf-8', 'ignore').replace('\x00', '-').strip('-')
                        color = struct.unpack('4B', light_data[32:36])
                    else:
                        chunk = struct.unpack('2i', light_data[0:8])
                        chunk_radius = struct.unpack('i', light_data[8:12])[0]
                        position = struct.unpack('3f', light_data[12:24])
                        light_radius = struct.unpack('f', light_data[24:28])[0] / 36
                        light_dropoff = struct.unpack('f', light_data[28:32])[0] / 36
                        light_name = light_data[32:60].decode('utf-8', 'ignore').replace('\x00', '-').strip('-')
                        color = (255, 255, 255, 255)  # Default white color for old format without explicit color

                    if any(math.isnan(coord) for coord in position):
                        logger.debug(f"Converting NaN values to 0 in file {file_path} at light {len(lights)}")
                        position = [0 if math.isnan(coord) else coord for coord in position]
                    
                    if abs(position[0]) > MAX_COORD or abs(position[1]) > MAX_COORD:
                        position = [coord / 2 for coord in position]

                    if light_name.strip('-') and (is_valid_light(position, color) and has_valid_coordinates(position)):
                        lights.append({
                            "chunk": chunk,
                            "chunk_radius": chunk_radius,
                            "position": {
                                "x": position[0] / 36,
                                "y": position[2] / 36,  # Swap y and z
                                "z": position[1] / 36  # Swap z and y
                            },
                            "light_radius": light_radius,
                            "light_dropoff": light_dropoff,
                            "light_name": light_name,
                            "color": color
                        })
                    else:
                        unknown_data_chunks.append(light_data.hex())
                except struct.error as e:
                    logger.error(f"Struct error reading light {i}: {e}")
                    unknown_data_chunks.append(light_data.hex())
            
            for unknown_data in unknown_data_chunks:
                analyze_unknown_data(unknown_data)

            return {
                "version": version,
                "light_count": actual_light_count,
                "lights": lights,
                "unknown_data_chunks": unknown_data_chunks
            }
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None

# Main processing function
def process_lit_files(input_dir, output_dir, map_size=4096, show_radius=True, track_empty_named_lights=True, opacity=20, background_color='white', generate_3d_objects=False, max_lights=256):
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.lit'):
                input_file = os.path.join(root, file)
                relative_path = os.path.relpath(root, input_dir)
                output_json_file = os.path.join(output_dir, relative_path, f"{os.path.splitext(file)[0]}.json")
                output_image_file = os.path.join(output_dir, relative_path, f"{os.path.splitext(file)[0]}.png")
                output_txt_file = os.path.join(output_dir, relative_path, f"{os.path.splitext(file)[0]}.txt")
                output_invalid_data_file = os.path.join(output_dir, relative_path, f"{os.path.splitext(file)[0]}_unknown_data.txt")

                os.makedirs(os.path.dirname(output_json_file), exist_ok=True)
                os.makedirs(os.path.dirname(output_image_file), exist_ok=True)
                os.makedirs(os.path.dirname(output_txt_file), exist_ok=True)
                os.makedirs(os.path.dirname(output_invalid_data_file), exist_ok=True)

                try:
                    data = read_lit_file(input_file, max_lights, track_empty_named_lights)
                    if data:
                        valid_lights = data["lights"]
                        export_to_json(data, output_json_file)
                        export_to_txt(data, output_txt_file)

                        if generate_3d_objects:
                            export_to_obj(valid_lights, output_invalid_data_file)

                        # Export unknown data chunks
                        with open(output_invalid_data_file, 'w') as file:
                            for unknown_data in data["unknown_data_chunks"]:
                                file.write(f"{unknown_data}\n")

                        logger.info(f"Processed {input_file} to {output_json_file}, {output_txt_file}")
                    else:
                        logger.warning(f"Skipped file {input_file} due to errors")
                except Exception as e:
                    logger.error(f"Error processing file {input_file}: {e}")

def generate_images(output_dir, map_size, show_radius, opacity, background_color):
    try:
        subprocess.run([
            'python', 'generate_images.py',
            output_dir,
            output_dir,
            '--map_size', str(map_size),
            '--opacity', str(opacity),
            '--background_color', background_color
        ] + (['--show_radius'] if show_radius else []), check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error generating images: {e}")

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
    
    process_lit_files(args.input_dir, args.output_dir, args.map_size, args.show_radius, args.track_empty_named_lights, args.opacity, args.background_color, args.generate_3d_objects)
    generate_images(args.output_dir, args.map_size, args.show_radius, args.opacity, args.background_color)

if __name__ == "__main__":  
    main()
