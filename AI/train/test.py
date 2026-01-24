import os
from PIL import Image
from torchvision import transforms
import random

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

INPUT_DIR = "goal"  # Input folder containing original images
OUTPUT_DIR = "goal_augmented"  # Output folder for augmented images
NUM_COPIES = 3  # Number of augmented copies per image
IMG_SIZE = 100  # Target image size

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ------------------------------------------------------------
# AUGMENTATION PIPELINE (Focus on brightness)
# ------------------------------------------------------------

def get_augmentation_transform():
    """Returns a transform pipeline with high brightness augmentation."""
    return transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.RandomRotation(20),
        transforms.ColorJitter(brightness=0.5, contrast=0.4, saturation=0.3, hue=0.1),
        transforms.RandomPerspective(distortion_scale=0.15, p=0.15),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
    ])

# ------------------------------------------------------------
# PROCESS IMAGES
# ------------------------------------------------------------

# Get all image files from input directory
image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')
image_files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(image_extensions)]

print(f"Found {len(image_files)} images in '{INPUT_DIR}'")
print(f"Generating {NUM_COPIES} augmented copies per image...\n")

total_generated = 0

for image_file in image_files:
    # Load original image
    image_path = os.path.join(INPUT_DIR, image_file)
    img = Image.open(image_path).convert('RGB')
    
    # Get filename without extension
    filename_base = os.path.splitext(image_file)[0]
    
    # Generate multiple augmented copies
    for copy_num in range(NUM_COPIES):
        # Apply augmentation
        transform = get_augmentation_transform()
        augmented_img = transform(img)
        
        # Save augmented image
        output_filename = f"{filename_base}_aug{copy_num + 1}.png"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        augmented_img.save(output_path)
        
        total_generated += 1
    
    print(f"✓ Processed '{image_file}' -> {NUM_COPIES} copies")

print(f"\n{'='*50}")
print(f"Augmentation complete!")
print(f"Total images generated: {total_generated}")
print(f"Output directory: '{OUTPUT_DIR}'")
print(f"{'='*50}")
