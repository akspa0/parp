import os
import json
import logging
import re

logger = logging.getLogger()

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
                    logger.debug(f"Writing light: {light_name} at position: {position}")
                    txt_file.write(f"{light_name},{position['x']},{position['y']},{position['z']},{color[0]},{color[1]},{color[2]},{color[3]},{light['light_radius']},{light['light_dropoff']}\n")
                except KeyError as e:
                    logger.error(f"Error writing light: {light} (KeyError: {e})")
            txt_file.write("\nInvalid Lights:\n")
            for light in data["bad_lights"]:
                try:
                    if 'raw_data' in light:
                        txt_file.write(f"Raw Data: {light['raw_data']}\n")
                    else:
                        position = light["position"]
                        color = light["color"]
                        light_name = f"Invalid Light {position[0]}_{position[1]}_{position[2]}"
                        logger.debug(f"Writing invalid light: {light_name} at position: {position}")
                        txt_file.write(f"{light_name},{position[0]},{position[1]},{position[2]},{color[0]},{color[1]},{color[2]},{color[3]},{light['light_radius']},{light['light_dropoff']}\n")
                except KeyError as e:
                    logger.error(f"Error writing invalid light: {light} (KeyError: {e})")
    except Exception as e:
        logger.error(f"Error writing TXT file {output_filename}: {e} ({type(e).__name__})")
