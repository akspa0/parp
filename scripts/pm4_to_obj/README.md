# PM4 Parser and 3D Object Creator

This project provides two scripts to parse PM4 files, extract relevant data, and generate 3D objects and textures. The workflow is divided into two main steps:

1. **Parsing the PM4 file to JSON**
2. **Creating 3D objects and textures from the parsed data**

## Requirements

- Python 3.x
- numpy
- Pillow
- scipy
- scikit-learn

You can install the required packages using pip:

```sh
pip install numpy pillow scipy
```

## Usage

### Step 1: Parsing the PM4 File

Use the `pm4_parser.py` script to parse the PM4 file and save the parsed data to a JSON file.

#### Command

```sh
python pm4_parser.py <path_to_pm4_file> <output_folder>
```

#### Example

```sh
python pm4_parser.py /path/to/your/pm4/file /path/to/output/folder
```

This command will create a `parsed_data.json` file in the specified output folder.

### Step 2: Creating 3D Objects and Textures

Use the `create_3d_obj.py` script to create 3D objects and textures from the parsed data JSON file.

#### Command

```sh
python create_3d_obj.py <path_to_parsed_data_json> <output_folder>
```

#### Example

```sh
python create_3d_obj.py /path/to/output/folder/parsed_data.json /path/to/output/folder
```

This command will generate the following files in the specified output folder:

- `combined_layer.obj`: The combined 3D object with vertices and normals.
- `texture.png`: The texture file created from the color data.
- `msvt_layer.obj`: The 3D object created from the MSVT chunk data.
- `mprl_layer.obj`: The 3D object created from the MPRL chunk data.
- Additional OBJ files for other chunks, if applicable.

## Script Details

### pm4_parser.py

This script parses the PM4 file and extracts relevant data into a JSON file. It handles the following chunks:

- `VPSM`: Vertex positions
- `IPSM`: Indices
- `NCSM`: Normals
- `KLSM`: Colors
- `MSVT`: Additional vertex positions with coordinate transformations
- `MPRL`: Additional data entries

### create_3d_obj.py

This script reads the JSON file created by the parser script and generates 3D object files and textures. It handles the following:

- Combines vertices and normals into a single OBJ file
- Creates textures from color data
- Creates separate OBJ files for MSVT and MPRL data
- Processes additional chunks and creates separate OBJ files if they contain vertex data

## Troubleshooting

### Common Errors

- **Cannot reshape array**: This error occurs if the chunk data size is not a multiple of the expected element size. The script attempts to handle and log these cases.
- **Insufficient vertices**: Some chunks may not contain enough data to form valid 3D objects. The script will attempt to interpolate data where possible and skip chunks that cannot be processed.

### Debugging

- Ensure that your PM4 file is valid and correctly formatted. [lol]
- Check the console output for specific error messages and warnings.
- Verify that the required Python packages are installed and up-to-date.