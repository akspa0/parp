import os
import argparse
from pywavefront import Wavefront

def invert_z_axis(obj_file):
    scene = Wavefront(obj_file)
    for i, vertex in enumerate(scene.vertices):
        scene.vertices[i] = [vertex[0], vertex[1], -vertex[2]]  # Inverting z-axis
    return scene

def invert_z_axis_in_folder(input_folder, output_folder):
    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Iterate through all files in the input folder
    for filename in os.listdir(input_folder):
        if filename.endswith(".obj"):
            input_file = os.path.join(input_folder, filename)
            output_file = os.path.join(output_folder, filename)
            inverted_scene = invert_z_axis(input_file)
            
            # Save inverted mesh
            with open(output_file, "w") as f:
                for v in inverted_scene.vertices:
                    f.write("v {} {} {}\n".format(v[0], v[1], v[2]))

                for line in inverted_scene.materials:
                    f.write(line + "\n")

                for mesh in inverted_scene.mesh_list:
                    for f in mesh.faces:
                        f_str = " ".join(str(v) for v in f)
                        f.write("f {}\n".format(f_str))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Invert z-axis coordinates of OBJ 3D meshes.")
    parser.add_argument("input_folder", help="Path to the folder containing input OBJ files.")
    parser.add_argument("output_folder", help="Path to the folder where inverted OBJ files will be saved.")
    args = parser.parse_args()

    input_folder = args.input_folder
    output_folder = args.output_folder

    invert_z_axis_in_folder(input_folder, output_folder)
