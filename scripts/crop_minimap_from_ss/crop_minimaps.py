import os
import cv2
import numpy as np
import argparse
from PIL import Image

def detect_and_crop_minimap(image_path, output_path):
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error loading image {image_path}")
        return

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 5)

    rows = gray.shape[0]

    # Detect circles in the image
    circles = cv2.HoughCircles(
        gray, cv2.HOUGH_GRADIENT, dp=1, minDist=rows / 8,
        param1=100, param2=30, minRadius=20, maxRadius=100
    )

    if circles is not None:
        circles = np.uint16(np.around(circles))
        for i in circles[0, :]:
            center = (i[0], i[1])  # Center of the circle
            radius = i[2]  # Radius of the circle

            # Calculate crop area, ensure it is within image bounds
            x = max(0, int(center[0] - radius))
            y = max(0, int(center[1] - radius))
            w = min(int(radius * 2), img.shape[1] - x)
            h = min(int(radius * 2), img.shape[0] - y)

            if w > 0 and h > 0 and x + w <= img.shape[1] and y + h <= img.shape[0]:
                crop_img = img[y:y+h, x:x+w]
                crop_img = cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB)
                crop_pil_img = Image.fromarray(crop_img)
                crop_pil_img.save(output_path)
                print(f"Cropped and saved minimap to {output_path}")
                return
            else:
                print(f"Invalid crop dimensions for {image_path} with center at {center} and radius {radius}")

    print(f"No minimap detected in {image_path}")

def process_images(input_folder, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    for root, _, files in os.walk(input_folder):
        for filename in files:
            if filename.endswith(('.jpg', '.jpeg', '.png')):
                img_path = os.path.join(root, filename)
                relative_path = os.path.relpath(root, input_folder)
                output_dir = os.path.join(output_folder, relative_path)
                
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                
                output_path = os.path.join(output_dir, filename)
                detect_and_crop_minimap(img_path, output_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Detect and crop minimap area from images.')
    parser.add_argument('input_folder', type=str, help='Path to the input folder containing images')
    parser.add_argument('output_folder', type=str, help='Path to the output folder to save cropped images')

    args = parser.parse_args()
    
    process_images(args.input_folder, args.output_folder)
