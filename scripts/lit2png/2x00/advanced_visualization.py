import os
import json
import logging
import argparse
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

# Constants
MAX_COORD = 17066
MIN_TEXT_SIZE = 16  # Minimum text size in points

# Setup logging to file and console
log_filename = f"advanced_visualization_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler(log_filename),
    logging.StreamHandler()
])
logger = logging.getLogger()

def create_gradient_image(lights, output_filename, map_size=4096, background_color='white'):
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
            base_opacity = 255
            for r in range(radius, 0, -1):
                adjusted_color = (color[0], color[1], color[2], int(base_opacity * (r / radius)))
                try:
                    draw.ellipse((x - r, y - r, x + r, y + r), fill=adjusted_color)
                except Exception as e:
                    logger.error(f"Error drawing ellipse at ({x}, {y}) with radius {r}: {e}")

        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        image.save(output_filename)
    except Exception as e:
        logger.error(f"Error creating gradient image {output_filename}: {e}")

def create_3d_visualization(lights, output_filename):
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    
    for light in lights:
        position = light["position"]
        color = light["color"]
        light_radius = light["light_radius"]
        
        ax.scatter(position['x'], position['z'], position['y'], c=[(color[0]/255, color[1]/255, color[2]/255)], s=light_radius*10)
    
    ax.set_xlabel('X')
    ax.set_ylabel('Z')
    ax.set_zlabel('Y')
    
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    plt.savefig(output_filename)

def process_json_files(input_dir, output_dir, visualization_type, map_size=4096, background_color='white'):
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.json'):
                input_file = os.path.join(root, file)
                relative_path = os.path.relpath(root, input_dir)
                output_image_file = os.path.join(output_dir, relative_path, f"{os.path.splitext(file)[0]}_{visualization_type}.png")

                os.makedirs(os.path.dirname(output_image_file), exist_ok=True)

                try:
                    with open(input_file, 'r', encoding='utf-8') as json_file:
                        data = json.load(json_file)
                        valid_lights = data["lights"]
                        if visualization_type == 'gradient':
                            create_gradient_image(valid_lights, output_image_file, map_size, background_color)
                        elif visualization_type == '3d':
                            create_3d_visualization(valid_lights, output_image_file)
                        logger.info(f"Processed {input_file} to {output_image_file}")
                except Exception as e:
                    logger.error(f"Error processing file {input_file}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate advanced visualizations from JSON files containing light data.")
    parser.add_argument('input_dir', help="Directory containing JSON files")
    parser.add_argument('output_dir', help="Directory to save visualization files")
    parser.add_argument('visualization_type', choices=['gradient', '3d'], help="Type of visualization to create (gradient or 3d)")
    parser.add_argument('--map_size', type=int, default=4096, help="Size of the map in pixels")
    parser.add_argument('--background_color', type=str, default='white', help="Background color of the image (white or black)")

    args = parser.parse_args()

    process_json_files(args.input_dir, args.output_dir, args.visualization_type, args.map_size, args.background_color)
