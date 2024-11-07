# Image Stitcher

This script stitches together multiple image tiles into a single large image. It processes image tiles from a specified input folder and combines them into a new image based on the given tile size.

## Features

- Automatically calculates the dimensions of the output image based on the number of tiles.
- Places each tile in its correct position within the output image.
- Supports tiles of any size (default is 257x257 pixels).
- Outputs a single stitched image.

## Requirements

- Python 3.x
- Pillow (PIL) library

## Installation

1. Clone this repository or download the script files.
2. Install the required dependencies using pip:
    ```bash
    pip install pillow
    ```

## Usage

Run the script with the following command-line arguments:

```bash
python tileJoiner0x00.py --input-folder <input_folder> --output-image <output_image> --tile-size <tile_size>
Arguments
--input-folder: Path to the folder containing image tiles (required).

--output-image: Path to save the output image (required).

--tile-size: Size of each tile in pixels (default: 257).

Example
```bash
python tileJoiner0x00.py --input-folder ./tiles --output-image stitched_image.png --tile-size 257
This command will stitch together the image tiles from the ./tiles folder into a single image and save it as stitched_image.png.

Notes
The script assumes that the tile filenames follow the pattern prefix_x_y.png, where x and y are the tile coordinates.

Make sure the input folder contains all the necessary tiles for the output image.