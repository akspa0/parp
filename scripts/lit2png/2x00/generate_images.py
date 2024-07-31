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

def create_image_from_lights(lights, output_filename, map_size=4096, show_radius=True, opacity=20, background_color='white'):
    try:
        bg_color = (0, 0, 0, 255) if background_color.lower() == 'black' else (255, 255, 255, 255)
        text_color = (255, 255, 255) if background_color.lower() == 'black' else (0, 0, 0)
        image = Image.new('RGBA', (map_size, map_size), bg_color)
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("arial.ttf", MIN_TEXT_SIZE)
            legend_font = ImageFont.truetype("arial.ttf", MIN_TEXT_SIZE)
        except IOError:
            font = ImageFont.load_default()
            legend_font = ImageFont.load_default()

        # Filter for valid lights in the south-east quadrant
        valid_lights = [light for light in lights if light['light_name'].strip('-') and any(light['position'].values()) and light['position']['x'] >= 0 and light['position']['y'] >= 0]

        for light in valid_lights:
            position = light["position"]
            x = int((position["x"] + MAX_COORD) / (2 * MAX_COORD) * (map_size - 1))
            y = int((position["y"] + MAX_COORD) / (2 * MAX_COORD) * (map_size - 1))
            radius = int((light["light_radius"] / MAX_COORD) * map_size)
            color = light["color"]
            base_opacity = int((opacity / 100) * 255)
            adjusted_color = (color[0], color[1], color[2], base_opacity)
            if show_radius:
                draw_circle_outline(draw, x, y, radius, adjusted_color)
            draw.rectangle((x - 2, y - 2, x + 2, y + 2), fill=adjusted_color)
            draw.text((x + 5, y), light["light_name"], fill=text_color, font=font)

        # Calculate dynamic swatch size and positions
        max_swatch_height = map_size // 3
        legend_start_x = 10
        legend_start_y = 10
        legend_height = len(valid_lights) * 80  # Approximate space needed
        if legend_height > max_swatch_height:
            swatch_size = max(max_swatch_height // len(valid_lights), MIN_TEXT_SIZE)
            legend_spacing = swatch_size + 10
        else:
            swatch_size = 64
            legend_spacing = 74

        legend_font = ImageFont.truetype("arial.ttf", MIN_TEXT_SIZE) if MIN_TEXT_SIZE >= 10 else ImageFont.load_default()

        # Draw the legend on the left side of the image
        draw.rectangle([legend_start_x, legend_start_y, legend_start_x + 300, legend_start_y + (len(valid_lights) + 1) * legend_spacing], fill=(255, 255, 255, 200), outline="black")
        draw.text((legend_start_x + 10, legend_start_y + 5), "Legend:", fill=text_color, font=legend_font)

        for i, light in enumerate(valid_lights):
            color = (light['color'][0], light['color'][1], light['color'][2], base_opacity)
            swatch_y = legend_start_y + (i + 1) * legend_spacing
            draw.rectangle([legend_start_x + 10, swatch_y, legend_start_x + 10 + swatch_size, swatch_y + swatch_size], fill=color, outline="black")  # Dynamic swatch size
            draw.text((legend_start_x + 10 + swatch_size + 10, swatch_y + (swatch_size // 4)), f"{light['light_name']}", fill=text_color, font=legend_font)

        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        image.save(output_filename)
    except Exception as e:
        logger.error(f"Error creating image {output_filename}: {e}")

def process_json_files(input_dir, output_dir, map_size=4096, show_radius=True, opacity=20, background_color='white'):
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
                        create_image_from_lights(valid_lights, output_image_file, map_size, show_radius, opacity, background_color)
                        logger.info(f"Processed {input_file} to {output_image_file}")
                except Exception as e:
                    logger.error(f"Error processing file {input_file}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate images from JSON files containing light data.")
    parser.add_argument('input_dir', help="Directory containing JSON files")
    parser.add_argument('output_dir', help="Directory to save PNG files")
    parser.add_argument('--map_size', type=int, default=4096, help="Size of the map in pixels")
    parser.add_argument('--show_radius', action='store_true', help="Enable/disable light radius visualization")
    parser.add_argument('--opacity', type=int, default=20, help="Set the opacity of light color blobs (0-100)")
    parser.add_argument('--background_color', type=str, default='white', help="Background color of the image (white or black)")

    args = parser.parse_args()

    process_json_files(args.input_dir, args.output_dir, args.map_size, args.show_radius, args.opacity, args.background_color)
