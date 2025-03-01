from PIL import Image
import os
import glob
import re

def stitch_tiles(input_folder, tile_size, suffix=''):
    """
    Stitch tiles from a specific folder with a given suffix.
    
    Args:
        input_folder (str): Path to the folder containing image tiles
        tile_size (int): Size of each tile
        suffix (str, optional): Suffix to filter tiles (e.g., '_height', '_layer1')
    
    Returns:
        PIL.Image or None: Stitched image or None if no tiles found
    """
    # Construct a regex pattern to match the base filename with the specific suffix
    base_pattern = r'(.*?)_(\d+)_(\d+)' + re.escape(suffix) + r'\.png$'
    
    # Get a list of matching image files
    tile_paths = sorted(glob.glob(os.path.join(input_folder, f"*{suffix}.png")))
    
    if not tile_paths:
        print(f"No tiles found with suffix: {suffix}")
        return None
    
    # Extract base filename
    base_filename = os.path.basename(tile_paths[0])
    match = re.match(base_pattern, base_filename)
    if not match:
        print(f"Error: Could not parse filename pattern for suffix {suffix}")
        return None
    
    # Determine the maximum x and y indices
    max_x_index = max([int(re.match(base_pattern, os.path.basename(path)).group(2)) for path in tile_paths])
    max_y_index = max([int(re.match(base_pattern, os.path.basename(path)).group(3)) for path in tile_paths])
    
    # Create a new image with the correct dimensions
    new_image_width = (max_x_index + 1) * tile_size
    new_image_height = (max_y_index + 1) * tile_size
    new_image = Image.new("RGBA", (new_image_width, new_image_height), (255, 255, 255, 0))
    
    print(f"New image dimensions: {new_image_width} x {new_image_height}")
    
    # Paste each tile into the new image
    for tile_path in tile_paths:
        tile = Image.open(tile_path)
        # Ensure tile is in RGBA mode
        if tile.mode != 'RGBA':
            tile = tile.convert('RGBA')
        
        filename = os.path.basename(tile_path)
        match = re.match(base_pattern, filename)
        
        x_index = int(match.group(2))
        y_index = int(match.group(3))
        
        x = x_index * tile_size
        y = y_index * tile_size
        new_image.paste(tile, (x, y), tile)
        print(f"Pasted tile at: ({x}, {y})")
    
    return new_image

def main(input_folder, output_dir, tile_size=256):
    """
    Main function to stitch tiles with height and layers.
    
    Args:
        input_folder (str): Path to the folder containing image tiles
        output_dir (str): Directory to save output images
        tile_size (int, optional): Size of each tile. Defaults to 256.
    """
    # Find a sample tile to extract base filename
    sample_tiles = glob.glob(os.path.join(input_folder, "*.png"))
    if not sample_tiles:
        print("No PNG tiles found in the input folder.")
        return
    
    # Extract base name from the first tile, removing the coordinate part
    first_tile = os.path.basename(sample_tiles[0])
    match = re.match(r'(.*?)_\d+_\d+(?:_\w+)?\.png', first_tile)
    
    if not match:
        print("Could not determine base filename from tiles.")
        return
    
    base_name = match.group(1)
    
    # Suffixes to process and their output names
    suffixes_and_outputs = [
        ('', ''),
        ('_height', '_height'),
        ('_layer1', '_layer1'),
        ('_layer2', '_layer2'),
        ('_layer3', '_layer3')
    ]
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Stitch and save images for each suffix
    for suffix, output_suffix in suffixes_and_outputs:
        stitched_image = stitch_tiles(input_folder, tile_size, suffix)
        if stitched_image:
            # Construct output filename
            output_filename = f"{base_name}{output_suffix}.png"
            output_path = os.path.join(output_dir, output_filename)
            
            # Save the image
            stitched_image.save(output_path)
            print(f"Saved image at: {output_path}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Stitch image tiles into separate PNG files with support for height and layer suffixes.")
    parser.add_argument("--input-folder", required=True, help="Path to the folder containing image tiles")
    parser.add_argument("--output", required=True, help="Directory to save output images")
    parser.add_argument("--tile-size", type=int, default=256, help="Size of each tile")
    args = parser.parse_args()

    main(args.input_folder, args.output, args.tile_size)
