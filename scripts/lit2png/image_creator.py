import os
import logging
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger()

MAX_COORD = 17066

def draw_circle_outline(draw, x, y, radius, color):
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=color)

def create_image_from_lights(lights, output_filename, map_size=4096, show_radius=True, opacity=20, background_color='white'):
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

        lights = sorted(lights, key=lambda l: (l['light_radius'], l['light_name']), reverse=True)

        for light in lights:
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

        legend_start_x = 10
        legend_start_y = 10
        legend_spacing = 72  # Increase spacing for larger swatches
        draw.rectangle([legend_start_x, legend_start_y, legend_start_x + 600, legend_start_y + (len(lights) + 2) * legend_spacing], fill=(255, 255, 255, 200))
        draw.text((legend_start_x + 10, legend_start_y + 5), "Legend:", fill=text_color, font=legend_font)
        for i, light in enumerate(lights):
            color = (light['color'][0], light['color'][1], light['color'][2], base_opacity)
            swatch_x = legend_start_x + 10
            swatch_y = legend_start_y + (i + 1) * legend_spacing
            draw.rectangle([swatch_x, swatch_y, swatch_x + 64, swatch_y + 64], fill=color)  # Swatch size 64x64
            draw.text((swatch_x + 74, swatch_y + 16), f"{light['light_name']}", fill=text_color, font=legend_font)

        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        image.save(output_filename)
    except Exception as e:
        logger.error(f"Error creating image {output_filename}: {e}")
