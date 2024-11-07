from PIL import Image
import os
import glob

def stitch_tiles(input_folder, tile_size, output_image_path):
    # Get a list of all image files in the input folder
    tile_paths = sorted(glob.glob(os.path.join(input_folder, "*.png")))
    
    # Determine the maximum x and y indices from the tile filenames
    max_x_index = max([int(os.path.basename(path).split('_')[1]) for path in tile_paths])
    max_y_index = max([int(os.path.basename(path).split('_')[2].split('.')[0]) for path in tile_paths])
    
    # Create a new image with the correct dimensions
    new_image_width = (max_x_index + 1) * tile_size
    new_image_height = (max_y_index + 1) * tile_size
    new_image = Image.new("RGB", (new_image_width, new_image_height), (255, 255, 255))
    
    print(f"New image dimensions: {new_image_width} x {new_image_height}")
    
    # Paste each tile into the new image
    for tile_path in tile_paths:
        tile = Image.open(tile_path)
        x_index = int(os.path.basename(tile_path).split('_')[1])
        y_index = int(os.path.basename(tile_path).split('_')[2].split('.')[0])
        x = x_index * tile_size
        y = y_index * tile_size
        new_image.paste(tile, (x, y))
        print(f"Pasted tile at: ({x}, {y})")
    
    # Save the new image
    new_image.save(output_image_path)
    print(f"Stitched image saved at: {output_image_path}")

def main(input_folder, output_image_path, tile_size=257):
    stitch_tiles(input_folder, tile_size, output_image_path)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Stitch image tiles into one large image.")
    parser.add_argument("--input-folder", required=True, help="Path to the folder containing image tiles")
    parser.add_argument("--output-image", required=True, help="Path to save the output image")
    parser.add_argument("--tile-size", type=int, default=257, help="Size of each tile")
    args = parser.parse_args()

    main(args.input_folder, args.output_image, args.tile_size)
