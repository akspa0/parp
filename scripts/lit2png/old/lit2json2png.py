import os
import struct
import json
import math
import logging
import argparse
import re
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

MAX_COORD = 17066
MAX_LIGHTS = 256  # Maximum number of lights to consider

def is_valid_light(position, color):
    return any(coord != 0 for coord in position) or any(c != 0 for c in color)

def is_valid_name(name):
    return re.match(r'^[\w\s\-\.,]+$', name) is not None

def has_valid_coordinates(position):
    return all(len(str(abs(coord)).split('.')[-1]) <= 12 for coord in position)

def read_lit_file(file_path, track_empty_named_lights=True):
    bad_lights = []
    try:
        with open(file_path, 'rb') as file:
            header = file.read(4)
            version = struct.unpack('B', header[0:1])[0]
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
            
            # Calculate the actual light count based on file size
            file_size = os.path.getsize(file_path)
            actual_light_count = min((file_size - header_size) // entry_size, MAX_LIGHTS)
            
            logger.debug(f"File format: {file_format}")
            logger.debug(f"Version: {version}")
            logger.debug(f"Reported Light Count: {reported_light_count}")
            logger.debug(f"Calculated Actual Light Count: {actual_light_count}")
            
            lights = []
            unnamed_light_count = 0
            for i in range(actual_light_count):
                light_data = file.read(entry_size)
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
                
                if abs(position[0]) > 17066 or abs(position[1]) > 17066:
                    position = [coord / 2 for coord in position]

                if light_name == "Global Light" or (is_valid_light(position, color) and has_valid_coordinates(position)):
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
                    unnamed_light_count += 1
                    bad_lights.append({
                        "chunk": chunk,
                        "chunk_radius": chunk_radius,
                        "position": position,
                        "light_radius": light_radius,
                        "light_dropoff": light_dropoff,
                        "light_name": light_name,
                        "color": color
                    })
            
            return {
                "version": version,
                "light_count": actual_light_count,
                "lights": lights,
                "unnamed_light_count": unnamed_light_count,
                "bad_lights": bad_lights
            }
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None

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
            txt_file.write("Name,Position X,Position Y,Position Z,Color RGBA\n")
            for light in data["lights"]:
                position = light["position"]
                color = light["color"]
                light_name = re.sub(r'[^\x00-\x7F]+', '', light['light_name'])
                txt_file.write(f"{light_name},{position['x']},{position['y']},{position['z']},{color[0]},{color[1]},{color[2]},{color[3]}\n")
            txt_file.write("\nInvalid Lights:\n")
            for light in data["bad_lights"]:
                position = light["position"]
                color = light["color"]
                light_name = re.sub(r'[^\x00-\x7F]+', '', light['light_name'])
                txt_file.write(f"{light_name},{position[0]},{position[1]},{position[2]},{color[0]},{color[1]},{color[2]},{color[3]}\n")
    except Exception as e:
        logger.error(f"Error writing TXT file {output_filename}: {e}")

def draw_circle_outline(draw, x, y, radius, color):
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=color)

def create_image_from_lights(lights, unnamed_light_count, output_filename, map_size=4096, show_radius=True, opacity=20, background_color='white'):
    try:
        bg_color = (0, 0, 0, 255) if background_color.lower() == 'black' else (255, 255, 255, 255)
        text_color = (255, 255, 255) if background_color.lower() == 'black' else (0, 0, 0)
        image = Image.new('RGBA', (map_size, map_size), bg_color)
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("arial.ttf", 16)
            legend_font = ImageFont.truetype("arial.ttf", 32)
        except IOError:
            font = ImageFont.load_default()
            legend_font = ImageFont.load_default()

        # Sort lights by radius (largest first) and then alphabetically by name
        lights = sorted(lights, key=lambda l: (l['light_radius'], l['light_name']), reverse=True)

        # Separate named and unnamed lights
        named_lights = sorted([light for light in lights if is_valid_name(light['light_name'])], key=lambda l: l['light_name'])
        unnamed_lights = [light for light in lights if not is_valid_name(light['light_name'])]

        leftmost_light = min((light['position']['x'] for light in named_lights), default=MAX_COORD)

        for light in named_lights:
            position = light["position"]
            # Adjust coordinates to place 0,0 at the center of the map
            x = int((position["x"] + MAX_COORD) / (2 * MAX_COORD) * (map_size - 1))
            y = int((position["y"] + MAX_COORD) / (2 * MAX_COORD) * (map_size - 1))
            radius = int((light["light_radius"] / MAX_COORD) * map_size)
            color = light["color"]
            
            # Set the opacity for lights
            base_opacity = int((opacity / 100) * 255)
            adjusted_color = (color[0], color[1], color[2], base_opacity)
            
            if show_radius:
                draw_circle_outline(draw, x, y, radius, adjusted_color)
            draw.rectangle((x - 2, y - 2, x + 2, y + 2), fill=adjusted_color)
            draw.text((x + 5, y), light["light_name"], fill=text_color, font=font)

        # Draw unnamed lights
        for light in unnamed_lights:
            position = light["position"]
            # Adjust coordinates to place 0,0 at the center of the map
            x = int((position["x"] + MAX_COORD) / (2 * MAX_COORD) * (map_size - 1))
            y = int((position["y"] + MAX_COORD) / (2 * MAX_COORD) * (map_size - 1))
            radius = int((light["light_radius"] / MAX_COORD) * map_size)
            color = (255, 255, 255, 255) if light["color"] == (0, 0, 0, 0) else light["color"]
            
            # Set the opacity for lights
            base_opacity = int((opacity / 100) * 255)
            adjusted_color = (color[0], color[1], color[2], base_opacity)
            
            if show_radius:
                draw_circle_outline(draw, x, y, radius, adjusted_color)
            draw.rectangle((x - 2, y - 2, x + 2, y + 2), fill=adjusted_color)
        
        # Create legend
        legend_start_x = 10 if leftmost_light >= 0 else map_size - 610
        legend_start_y = 10
        legend_spacing = 40
        draw.rectangle([legend_start_x, legend_start_y, legend_start_x + 600, legend_start_y + (len(named_lights) + 2) * legend_spacing], fill=(255, 255, 255, 200))
        draw.text((legend_start_x + 10, legend_start_y + 5), "Legend:", fill=text_color, font=legend_font)
        for i, light in enumerate(named_lights):
            color = (light['color'][0], light['color'][1], light['color'][2], base_opacity)
            swatch_x = legend_start_x + 10
            swatch_y = legend_start_y + (i + 1) * legend_spacing
            draw.rectangle([swatch_x, swatch_y, swatch_x + 20, swatch_y + 20], fill=color)
            draw.text((swatch_x + 30, swatch_y), f"{light['light_name']}", fill=text_color, font=legend_font)

        # Add unnamed lights count
        if unnamed_light_count > 0:
            swatch_y = legend_start_y + (len(named_lights) + 1) * legend_spacing
            draw.text((legend_start_x + 10, swatch_y), f"Unnamed Lights: {unnamed_light_count}", fill=text_color, font=legend_font)
        
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        image.save(output_filename)
    except Exception as e:
        logger.error(f"Error creating image {output_filename}: {e}")

def process_lit_files(input_dir, output_dir, map_size=4096, show_radius=True, track_empty_named_lights=True, opacity=20, background_color='white'):
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.lit'):
                input_file = os.path.join(root, file)
                relative_path = os.path.relpath(root, input_dir)
                output_json_file = os.path.join(output_dir, relative_path, f"{os.path.splitext(file)[0]}.json")
                output_image_file = os.path.join(output_dir, relative_path, f"{os.path.splitext(file)[0]}.png")
                output_txt_file = os.path.join(output_dir, relative_path, f"{os.path.splitext(file)[0]}.txt")

                os.makedirs(os.path.dirname(output_json_file), exist_ok=True)
                os.makedirs(os.path.dirname(output_image_file), exist_ok=True)
                os.makedirs(os.path.dirname(output_txt_file), exist_ok=True)

                try:
                    data = read_lit_file(input_file, track_empty_named_lights)
                    if data:
                        export_to_json(data, output_json_file)
                        export_to_txt(data, output_txt_file)
                        create_image_from_lights(data["lights"], data["unnamed_light_count"], output_image_file, map_size, show_radius, opacity, background_color)
                        logger.info(f"Processed {input_file} to {output_json_file}, {output_image_file}, and {output_txt_file}")
                    else:
                        logger.warning(f"Skipped file {input_file} due to errors")
                except Exception as e:
                    logger.error(f"Error processing file {input_file}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Convert LIT files to JSON files and PNG visualizations.")
    parser.add_argument('input_dir', help="Directory containing LIT files")
    parser.add_argument('output_dir', help="Directory to save JSON and PNG files")
    parser.add_argument('--map_size', type=int, default=4096, help="Size of the map in pixels")
    parser.add_argument('--show_radius', action='store_true', help="Enable/disable light radius visualization")
    parser.add_argument('--track_empty_named_lights', action='store_true', default=True, help="Track lights with valid names but RGBA values of (0,0,0,0)")
    parser.add_argument('--opacity', type=int, default=20, help="Set the opacity of light color blobs (0-100)")
    parser.add_argument('--background_color', type=str, default='white', help="Background color of the image (white or black)")

    args = parser.parse_args()
    
    process_lit_files(args.input_dir, args.output_dir, args.map_size, args.show_radius, args.track_empty_named_lights, args.opacity, args.background_color)

if __name__ == "__main__":
    main()
