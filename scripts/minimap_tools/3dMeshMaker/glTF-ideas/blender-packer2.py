import bpy
import os
import shutil

# Path to your OBJ, MTL, and PNG files
obj_dir = r"E:\\WoW\\blendermaps\\out67-z\\"
mtl_dir = r"E:\\WoW\\blendermaps\\out67-z\\"
texture_dir = r"E:\\WoW\\blendermaps\\out67-z\\"

# Function to import OBJ with materials
def import_obj_with_materials(obj_file, mtl_file):
    bpy.ops.import_scene.obj(filepath=obj_file)
    # Assuming each OBJ file has its corresponding MTL file
    create_materials_from_mtl(mtl_file)

# Function to create materials from MTL files
def create_materials_from_mtl(mtl_file):
    with open(mtl_file, 'r') as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith('newmtl'):
                material_name = line.split()[1].strip()
                bpy.data.materials.new(name=material_name)
            elif line.startswith('map_Kd'):
                texture_path = os.path.join(texture_dir, line.split()[1].strip())
                material = bpy.data.materials.get(material_name)
                if material:
                    material.use_nodes = True
                    principled_bsdf = material.node_tree.nodes.get('Principled BSDF')
                    if principled_bsdf:
                        texture_node = material.node_tree.nodes.new('ShaderNodeTexImage')
                        texture_node.image = bpy.data.images.load(texture_path)
                        material.node_tree.links.new(principled_bsdf.inputs['Base Color'], texture_node.outputs['Color'])

# Function to arrange objects in a grid
def arrange_objects(obj_list):
    # Assuming obj_list is a list of (obj, x, y) tuples, where (x, y) are the coordinates in the grid
    for obj, x, y in obj_list:
        obj.location = (x, y, 0)  # Set object location based on coordinates
        # You may need to adjust the location based on your scene's scale and orientation

# Example usage
obj_files = [os.path.join(obj_dir, f) for f in os.listdir(obj_dir) if f.endswith('.obj')]
mtl_files = [os.path.join(mtl_dir, f) for f in os.listdir(mtl_dir) if f.endswith('.mtl')]

obj_list = []
for obj_file, mtl_file in zip(obj_files, mtl_files):
    # Extract coordinates from filename (assuming XX_YY.obj format)
    filename = os.path.splitext(os.path.basename(obj_file))[0]
    coords = filename.split('_')
    x, y = int(coords[0]), int(coords[1])
    import_obj_with_materials(obj_file, mtl_file)
    obj = bpy.context.selected_objects[0]
    obj_list.append((obj, x, y))
    bpy.ops.object.select_all(action='DESELECT')  # Deselect all objects for the next iteration

# Arrange objects in a grid
arrange_objects(obj_list)

# Save the Blender project
bpy.ops.wm.save_mainfile(filepath="E:\\WoW\\blendermaps\\prealpha2002-1.blend")
