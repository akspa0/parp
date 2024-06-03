from PIL import Image

# Load the image
image_path = "D:/WoW Stuff/Modding 2023/New folder/parp/images/upscaled_az_kl/preAlpha_over_0.5.3.png"
image = Image.open(image_path)

# Desired number of tiles
num_tiles = 903

# Calculate tile dimensions
tile_width = image.width // 24
tile_height = image.height // 43

# Function to save tiles
def save_tile(image, left, upper, right, lower, x, y):
    # Ensure the crop area does not exceed the image dimensions
    right = min(right, image.width)
    lower = min(lower, image.height)
    tile = image.crop((left, upper, right, lower)).resize((257, 257), Image.BILINEAR)
    tile_filename = f"prealpha_ek_{x}_{y}_vcol.png"
    tile.save(f"D:/WoW Stuff/Modding 2023/New folder/parp/images/upscaled_az_kl/test/{tile_filename}")

# Loop through the specified coordinates and extract tiles
tiles_created = 0
for y in range(20, 63):
    for x in range(24, 45):
        left = (x - 24) * tile_width
        upper = (y - 20) * tile_height
        right = left + tile_width
        lower = upper + tile_height
        save_tile(image, left, upper, right, lower, x, y)
        tiles_created += 1
        if tiles_created == num_tiles:
            break
    else:
        continue
    break
