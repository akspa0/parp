import os
import json
import logging
import argparse
from datetime import datetime
import numpy as np
from PIL import Image
import math

# Constants
MAX_COORD = 17066

# Setup logging to file and console
log_filename = f"advanced_visualization_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler(log_filename),
    logging.StreamHandler()
])
logger = logging.getLogger()

def create_sphere(radius, lat_segments, lon_segments):
    vertices = []
    normals = []
    uvs = []
    indices = []

    for lat in range(lat_segments + 1):
        theta = lat * math.pi / lat_segments
        sin_theta = math.sin(theta)
        cos_theta = math.cos(theta)

        for lon in range(lon_segments + 1):
            phi = lon * 2 * math.pi / lon_segments
            sin_phi = math.sin(phi)
            cos_phi = math.cos(phi)

            x = cos_phi * sin_theta
            y = cos_theta
            z = sin_phi * sin_theta
            u = lon / lon_segments
            v = lat / lat_segments

            vertices.append((radius * x, radius * y, radius * z))
            normals.append((x, y, z))
            uvs.append((u, v))

    for lat in range(lat_segments):
        for lon in range(lon_segments):
            first = lat * (lon_segments + 1) + lon
            second = first + lon_segments + 1

            indices.append((first + 1, second, first))
            indices.append((first + 1, second + 1, second))

    return vertices, normals, uvs, indices

def create_sphere_obj(lights, output_filename, sphere_radius=0.1, lat_segments=16, lon_segments=16):
    try:
        obj_file = output_filename + "_spheres.obj"
        mtl_file = output_filename + "_spheres.mtl"
        texture_file = output_filename + "_spheres_texture.png"

        # Generate vertices, normals, uvs, and indices for a sphere
        sphere_vertices, sphere_normals, sphere_uvs, sphere_indices = create_sphere(sphere_radius, lat_segments, lon_segments)

        # Prepare the texture
        colors = [light["color"] for light in lights]
        colors = np.array(colors, dtype=np.uint8)
        texture_size = (len(colors), 1, 3)
        if colors.size != texture_size[0] * texture_size[1] * texture_size[2]:
            logger.warning(f"Skipping texture generation for {output_filename} due to insufficient lights.")
            texture_image = None
        else:
            texture_image = Image.fromarray(colors.reshape(texture_size), 'RGB')
            texture_image.save(texture_file)

        with open(obj_file, 'w') as f:
            f.write(f"mtllib {os.path.basename(mtl_file)}\n")
            vertex_offset = 0

            for i, light in enumerate(lights):
                pos = light["position"]
                color = light["color"]

                for v in sphere_vertices:
                    f.write(f"v {v[0] + pos['x']} {v[1] + pos['y']} {v[2] + pos['z']}\n")
                for n in sphere_normals:
                    f.write(f"vn {n[0]} {n[1]} {n[2]}\n")
                for uv in sphere_uvs:
                    f.write(f"vt {uv[0]} {uv[1]}\n")

                f.write(f"usemtl Material{i}\n")
                f.write(f"g Sphere{i}\n")
                for idx in sphere_indices:
                    f.write(f"f {idx[0] + vertex_offset}/{idx[0] + vertex_offset}/{idx[0] + vertex_offset} {idx[1] + vertex_offset}/{idx[1] + vertex_offset}/{idx[1] + vertex_offset} {idx[2] + vertex_offset}/{idx[2] + vertex_offset}/{idx[2] + vertex_offset}\n")

                vertex_offset += len(sphere_vertices)

        with open(mtl_file, 'w') as f:
            for i, color in enumerate(colors):
                f.write(f"newmtl Material{i}\n")
                if texture_image:
                    f.write(f"map_Kd {os.path.basename(texture_file)}\n")
                f.write(f"Kd {color[0] / 255.0} {color[1] / 255.0} {color[2] / 255.0}\n")

        logger.info(f"Generated spheres OBJ file at {obj_file}")
        logger.info(f"Generated MTL file at {mtl_file}")
        if texture_image:
            logger.info(f"Generated spheres texture file at {texture_file}")

    except Exception as e:
        logger.error(f"Error creating spheres OBJ file: {e}")

def create_global_light(output_filename, direction=(0, -1, 0), color=(1.0, 1.0, 1.0)):
    try:
        obj_file = output_filename + "_global_light.obj"
        mtl_file = output_filename + "_global_light.mtl"

        with open(obj_file, 'w') as f:
            f.write(f"mtllib {os.path.basename(mtl_file)}\n")
            f.write("v 0.0 0.0 0.0\n")  # Placeholder vertex
            f.write("vn 0.0 0.0 0.0\n")  # Placeholder normal
            f.write(f"l 1 {direction[0]} {direction[1]} {direction[2]}\n")  # Light direction

        with open(mtl_file, 'w') as f:
            f.write("newmtl GlobalLight\n")
            f.write(f"Kd {color[0]} {color[1]} {color[2]}\n")

        logger.info(f"Generated global light OBJ file at {obj_file}")
        logger.info(f"Generated global light MTL file at {mtl_file}")

    except Exception as e:
        logger.error(f"Error creating global light OBJ file: {e}")

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
                        global_light = data.get("global_light", None)
                        if visualization_type == 'obj':
                            create_sphere_obj(valid_lights, output_base)
                            if global_light:
                                create_global_light(output_base, direction=global_light["direction"], color=global_light["color"])
                        logger.info(f"Processed {input_file} to {output_base}_spheres.obj and {output_base}_global_light.obj")
                except Exception as e:
                    logger.error(f"Error processing file {input_file}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate OBJ files from JSON files containing light data.")
    parser.add_argument('input_dir', help="Directory containing JSON files")
    parser.add_argument('output_dir', help="Directory to save OBJ files")
    parser.add_argument('visualization_type', choices=['obj'], help="Type of visualization to create (obj)")

    args = parser.parse_args()

    process_json_files(args.input_dir, args.output_dir, args.visualization_type)
