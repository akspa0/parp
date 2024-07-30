import os
import logging

logger = logging.getLogger()

def export_to_obj(lights, output_filename):
    os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    try:
        with open(output_filename, 'w') as obj_file:
            obj_file.write("# OBJ file\n")
            for light in lights:
                position = light["position"]
                light_radius = light["light_radius"]
                color = light["color"]
                # Writing vertex (point)
                obj_file.write(f"v {position['x']} {position['z']} {position['y']} {color[0] / 255} {color[1] / 255} {color[2] / 255}\n")
                # Writing additional data as comment
                obj_file.write(f"# light_radius {light_radius}\n")
                obj_file.write(f"# light_dropoff {light['light_dropoff']}\n")
        logger.info(f"Exported {len(lights)} lights to {output_filename}")
    except Exception as e:
        logger.error(f"Error writing OBJ file {output_filename}: {e}")
