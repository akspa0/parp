# Image Tile Processor

This tool processes an input image by cropping it into non-blank tiles and optionally combining the non-blank tiles into a new image. It also supports generating vertex color maps and zipping the output files.

## Features

- Crop an image into non-blank tiles.
- Optionally combine non-blank tiles into a new image.
- Generate vertex color maps with the `--vcol` option.
- Specify a custom prefix for output filenames.
- Zip the output folder and new image.

## Requirements

- Python 3.x
- Pillow library

## Installation

1. Clone the repository or download the script.
2. Install the required library using pip:

```sh
pip install pillow
```

## Usage

```sh
python image_tile_processor.py --input-image <input_image_path> --output-folder <output_folder> --prefix <filename_prefix> [options]
```

### Arguments

- `--input-image`: Path to the input image (required).
- `--output-folder`: Path to the output folder (required).
- `--prefix`: Prefix for the output filenames (required).
- `--tile-size`: Size of each tile (default: 128).
- `--no-combine`: Do not combine the outputs at the end (default: enabled).
- `--vcol`: Generate vertex color maps.

### Example

```sh
python image_tile_processor.py --input-image example.jpg --output-folder output --prefix example --tile-size 128 --vcol
```

This command will process the `example.jpg` image, crop it into non-blank tiles of size 128x128, generate vertex color maps, and save the output files with the prefix `example` in the `output` folder.

