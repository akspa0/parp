from PIL import Image
import os
import zipfile
Image.MAX_IMAGE_PIXELS = None

def crop_into_tiles(image, tile_size, output_folder, prefix, vcol=False):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    num_tiles_x = image.width // tile_size
    num_tiles_y = image.height // tile_size

    print(f"Number of tiles to process: {num_tiles_x} x {num_tiles_y}")

    non_blank_tiles = []
    for y in range(num_tiles_y):
        for x in range(num_tiles_x):
            left = x * tile_size
            upper = y * tile_size
            right = left + tile_size
            lower = upper + tile_size
            tile = image.crop((left, upper, right, lower))
            # Check if tile is blank or pure white
            if not is_blank_or_white(tile):
                suffix = "_vcol" if vcol else ""
                tile_path = os.path.join(output_folder, f"{prefix}_{x}_{y}{suffix}.png")
                tile.save(tile_path)
                print(f"Processed tile {x}_{y} saved at: {tile_path}")
                non_blank_tiles.append((left, upper, right, lower))

    return non_blank_tiles

def is_blank_or_white(tile):
    # Convert to grayscale for simplicity
    grayscale_tile = tile.convert('L')
    # Calculate mean pixel intensity
    mean_intensity = sum(grayscale_tile.getdata()) / float(tile.size[0] * tile.size[1])
    # Define threshold for blank or pure white
    threshold = 240
    return mean_intensity >= threshold

def zip_output_folder(input_image_path, output_folder, new_image_path):
    input_filename = os.path.splitext(os.path.basename(input_image_path))[0]
    output_folder_name = os.path.basename(output_folder)
    zip_filename = f"{input_filename}_{output_folder_name}.zip"
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for root, _, files in os.walk(output_folder):
            for file in files:
                zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), output_folder))
        
        # Add the new image file to the zip archive with a unique name if it's not already added
        new_image_filename = f"{input_filename}_new.png"
        if new_image_filename not in zipf.namelist():
            zipf.write(new_image_path, new_image_filename)

    print(f"Output folder and new image zipped and saved as: {zip_filename}")

def build_new_image(original_image, non_blank_tiles, tile_size):
    # Calculate the dimensions of the new image
    min_x = min(tile[0] for tile in non_blank_tiles)
    min_y = min(tile[1] for tile in non_blank_tiles)
    max_x = max(tile[2] for tile in non_blank_tiles)
    max_y = max(tile[3] for tile in non_blank_tiles)
    new_width = max_x - min_x + tile_size
    new_height = max_y - min_y + tile_size

    print(f"New image dimensions: {new_width} x {new_height}")

    # Create a new image with white background
    new_image = Image.new("RGB", (new_width, new_height), (255, 255, 255))
    
    # Paste non-blank tiles onto the new image
    for tile in non_blank_tiles:
        left, upper, right, lower = tile
        print(f"Pasting tile at coordinates: ({left - min_x}, {upper - min_y})")
        tile_image = original_image.crop((left, upper, right, lower))
        new_image.paste(tile_image, (left - min_x, upper - min_y))
    
    return new_image

def main(input_image_path, output_folder, tile_size=128, prefix="", combine=True, vcol=False):
    # Load the image
    original_image = Image.open(input_image_path)

    # Crop into tiles and get non-blank tiles
    non_blank_tiles = crop_into_tiles(original_image, tile_size, output_folder, prefix, vcol)

    if combine:
        # Build new image with non-blank tiles
        new_image = build_new_image(original_image, non_blank_tiles, tile_size)
        new_image_path = os.path.join(output_folder, f"{prefix}_new.png")
        new_image.save(new_image_path)
        print(f"New image saved at: {new_image_path}")

        # Zip output folder and new image
        zip_output_folder(input_image_path, output_folder, new_image_path)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Resize and crop image tiles.")
    parser.add_argument("--input-image", required=True, help="Path to the input image")
    parser.add_argument("--output-folder", required=True, help="Path to the output folder")
    parser.add_argument("--tile-size", type=int, default=128, help="Size of each tile")
    parser.add_argument("--prefix", required=True, help="Prefix for the output filenames")
    parser.add_argument("--no-combine", action='store_true', help="Do not combine the outputs at the end")
    parser.add_argument("--vcol", action='store_true', help="Generate vertex color maps")
    args = parser.parse_args()

    main(args.input_image, args.output_folder, args.tile_size, args.prefix, not args.no_combine, args.vcol)
