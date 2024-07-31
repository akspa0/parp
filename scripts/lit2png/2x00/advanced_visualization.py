import os
import json
import logging
from PIL import Image, ImageDraw, ImageFont
import argparse
from datetime import datetime

# Constants
MAX_COORD = 17066
MIN_TEXT_SIZE = 16  # Minimum text size in points

# Setup logging to file and console
log_filename = f"image_exporter_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler(log_filename),
    logging.StreamHandler()
])
logger = logging.getLogger()

def draw_circle_outline(draw, x, y, radius, color):
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=color)

def create_gas_giant_style_image(lights, output_filename, map_size=4096, opacity=20, background_color='white'):
    try:
        bg_color = (0, 0, 0, 255) if background_color.lower() == 'black' else (255, 255, 255, 255)
        image = Image.new('RGBA', (map_size, map_size), bg_color)
        draw = ImageDraw.Draw(image)
        
        for light in lights:
            position = light["position"]
            x = int((position["x"] + MAX_COORD) / (2 * MAX_COORD) * (map_size - 1))
            y = int((position["y"] + MAX_COORD) / (2 * MAX_COORD) * (map_size - 1))
            radius = int((light["light_radius"] / MAX_COORD) * map_size)
            color = light["color"]
            base_opacity = int((opacity / 100) * 255)

            # Create a gradient effect for the light falloff
            for i in range(radius, 0, -1):
                alpha = int((base_opacity * (i / radius)))
                falloff_color = (color[0], color[1], color[2], alpha)
                draw.ellipse((x - i, y - i, x + i, y + i), fill=falloff_color)

        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        image.save(output_filename)
        logger.info(f"Generated PNG image for {output_filename}")

    except Exception as e:
        logger.error(f"Error creating PNG image for {output_filename}: {e}")

def process_json_files(input_dir, output_dir, map_size=4096, opacity=20, background_color='white'):
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.json'):
                input_file = os.path.join(root, file)
                relative_path = os.path.relpath(root, input_dir)
                output_image_file = os.path.join(output_dir, relative_path, f"{os.path.splitext(file)[0]}.png")

                os.makedirs(os.path.dirname(output_image_file), exist_ok=True)

                try:
                    with open(input_file, 'r', encoding='utf-8') as json_file:
                        data = json.load(json_file)
                        valid_lights = data["lights"]
                        create_gas_giant_style_image(valid_lights, output_image_file, map_size, opacity, background_color)
                        logger.info(f"Processed {input_file} to {output_image_file}")
                except Exception as e:
                    logger.error(f"Error processing file {input_file}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate gas giant style images from JSON files containing light data.")
    parser.add_argument('input_dir', help="Directory containing JSON files")
    parser.add_argument('output_dir', help="Directory to save PNG files")
    parser.add_argument('--map_size', type=int, default=4096, help="Size of the map in pixels")
    parser.add_argument('--opacity', type=int, default=20, help="Set the opacity of light color blobs (0-100)")
    parser.add_argument('--background_color', type=str, default='white', help="Background color of the image (white or black)")

    args = parser.parse_args()

    process_json_files(args.input_dir, args.output_dir, args.map_size, args.opacity, args.background_color)
