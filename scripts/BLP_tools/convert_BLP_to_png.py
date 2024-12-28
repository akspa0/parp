#!/usr/bin/env python3

import os
import argparse
from pathlib import Path
from PIL import Image

def tile_image(image: Image.Image, tile_size=(1024, 1024)) -> Image.Image:
    """
    Tiles the original image across a new canvas of specified tile_size.

    Args:
        image (Image.Image): The original Pillow image to tile.
        tile_size (tuple): The size of the output image (width, height).

    Returns:
        Image.Image: The tiled Pillow image.
    """
    tile_width, tile_height = tile_size
    original_width, original_height = image.size

    # Create a new blank RGBA image
    new_image = Image.new('RGBA', (tile_width, tile_height))

    # Paste the original image repeatedly to fill the new canvas
    for x in range(0, tile_width, original_width):
        for y in range(0, tile_height, original_height):
            new_image.paste(image, (x, y))

    return new_image

def convert_blp_to_png(input_path: Path, output_path: Path, tile_1024: bool):
    """
    Convert a single BLP file to PNG with optional tiling.

    Args:
        input_path (Path): Path to the input .blp file.
        output_path (Path): Path where the output .png will be saved.
        tile_1024 (bool): Whether to tile the image to 1024x1024.
    """
    try:
        # Open the BLP file using Pillow
        with Image.open(input_path) as img:
            # Ensure the image is in RGBA mode to preserve alpha channel
            img = img.convert('RGBA')

            # Optionally tile the image
            if tile_1024:
                img = tile_image(img, (1024, 1024))

            # Ensure the output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Save as PNG
            img.save(output_path, 'PNG')
            print(f"Converted: {input_path} --> {output_path}")

    except Exception as e:
        print(f"Error processing {input_path}: {e}")

def process_directory(input_dir: Path, output_dir: Path, tile_1024: bool):
    """
    Recursively process all .blp files in the input directory.

    Args:
        input_dir (Path): Root directory containing .blp files.
        output_dir (Path): Root directory where .png files will be saved.
        tile_1024 (bool): Whether to tile images to 1024x1024.
    """
    if not input_dir.is_dir():
        print(f"Error: Input directory '{input_dir}' does not exist or is not a directory.")
        return

    # Walk through the input directory
    for root, dirs, files in os.walk(input_dir):
        root_path = Path(root)
        for file_name in files:
            if file_name.lower().endswith('.blp'):
                blp_path = root_path / file_name
                # Determine the relative path to maintain directory structure
                relative_path = blp_path.relative_to(input_dir).with_suffix('.png')
                out_path = output_dir / relative_path
                # Convert the BLP to PNG
                convert_blp_to_png(blp_path, out_path, tile_1024)

def main():
    parser = argparse.ArgumentParser(
        description="Recursively convert BLP texture files to PNG, preserving alpha channels and optionally tiling to 1024x1024."
    )
    parser.add_argument(
        "input_dir",
        type=str,
        help="Path to the input directory containing .blp files."
    )
    parser.add_argument(
        "output_dir",
        type=str,
        help="Path to the output directory where .png files will be saved."
    )
    parser.add_argument(
        "--tile-1024",
        action="store_true",
        help="If set, tile each texture to 1024x1024 pixels."
    )

    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    tile_1024 = args.tile_1024

    print(f"Input Directory: {input_dir}")
    print(f"Output Directory: {output_dir}")
    print(f"Tiling to 1024x1024: {'Enabled' if tile_1024 else 'Disabled'}")

    process_directory(input_dir, output_dir, tile_1024)

    print("Conversion complete.")

if __name__ == "__main__":
    main()
