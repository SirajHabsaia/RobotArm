import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from datetime import datetime
from tqdm.auto import tqdm
import random
from PIL import Image
import torchvision.utils as vutils

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

DATA_DIR = "../data"   # Resized dataset
PEEK = False
AUG_MODE = 1
# 0 = NO augmentation (only resize + normalize)
# 1 = Minimal augmentation (recommended)
# 2 = Strong augmentation
# 3 = Extreme augmentation (low quality camera simulation)

BATCH_SIZE = 32
LR = 0.0005
EPOCHS = 25
IMG_SIZE = 100

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ------------------------------------------------------------
# CUSTOM TRANSFORMS
# ------------------------------------------------------------

class RandomDownscale:
    """Randomly downscale image to simulate low quality camera."""
    def __init__(self, min_size=40, max_size=100, target_size=100):
        self.min_size = min_size
        self.max_size = max_size
        self.target_size = target_size
    
    def __call__(self, img):
        # Randomly choose a downscale size
        downscale_size = random.randint(self.min_size, self.max_size)
        # Downscale
        img_downscaled = img.resize((downscale_size, downscale_size), Image.BILINEAR)
        # Upscale back to target size
        img_upscaled = img_downscaled.resize((self.target_size, self.target_size), Image.BILINEAR)
        return img_upscaled


# ------------------------------------------------------------
# AUGMENTATION PIPELINES
# ------------------------------------------------------------

def get_transforms(mode):
    """Returns transform pipelines based on AUG_MODE."""
    
    if mode == 0:
        # No augmentation
        train_tf = transforms.Compose([
            transforms.Resize((IMG_SIZE, IMG_SIZE)),
            transforms.ToTensor(),
        ])
    
    elif mode == 1:
        # Minimal augmentation
        train_tf = transforms.Compose([
            transforms.Resize((IMG_SIZE, IMG_SIZE)),
            transforms.RandomRotation(10),
            transforms.ColorJitter(brightness=0.5, contrast=0.3, saturation=0.3),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
        ])
    
    elif mode == 2:
        # Strong augmentation
        train_tf = transforms.Compose([
            transforms.Resize((IMG_SIZE, IMG_SIZE)),
            transforms.RandomRotation(25),
            transforms.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.2),
            transforms.RandomPerspective(distortion_scale=0.4, p=0.4),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
        ])
    
    elif mode == 3:
        # Extreme augmentation (low quality camera simulation)
        train_tf = transforms.Compose([
            transforms.Resize((IMG_SIZE, IMG_SIZE)),
            RandomDownscale(min_size=40, max_size=100, target_size=IMG_SIZE),  # Simulate low quality camera
            transforms.RandomRotation(30),
            transforms.ColorJitter(brightness=0.6, contrast=0.6, saturation=0.3, hue=0.1),
            transforms.RandomPerspective(distortion_scale=0.5, p=0.5),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
        ])
    
    # Test set NEVER gets augmentation
    test_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
    ])

    return train_tf, test_tf


train_tf, test_tf = get_transforms(AUG_MODE)


# ------------------------------------------------------------
# DATASET LOADING
# ------------------------------------------------------------

train_data = datasets.ImageFolder(os.path.join(DATA_DIR, "train"), transform=train_tf)
test_data  = datasets.ImageFolder(os.path.join(DATA_DIR, "test"),  transform=test_tf)

train_loader = DataLoader(train_data, batch_size=BATCH_SIZE, shuffle=True)
test_loader  = DataLoader(test_data,  batch_size=BATCH_SIZE, shuffle=False)

CLASS_NAMES = train_data.classes
print("Classes:", CLASS_NAMES)


# ------------------------------------------------------------
# CNN MODEL (Light but powerful)
# ------------------------------------------------------------

class ChessCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 8, 3, padding=1), nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(8, 16, 3, padding=1), nn.ReLU(),
            nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(16 * 25 * 25, 32),  # Adjust if your input size changes
            nn.ReLU(),
            nn.Linear(32, 3)
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x


model = ChessCNN().to(DEVICE)

criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=LR)


# ------------------------------------------------------------
# TRAINING + VALIDATION LOOP
# ------------------------------------------------------------

# Create peek directory if it doesn't exist
PEEK_DIR = "peek"
os.makedirs(PEEK_DIR, exist_ok=True)

# Counter for saving peek images
global_image_counter = 0

best_acc = 0.0

for epoch in range(1, EPOCHS + 1):
    model.train()
    train_loss = 0

    print(f"\nEpoch {epoch}/{EPOCHS}")
    progress_bar = tqdm(train_loader, desc="Training", leave=False)

    for imgs, labels in progress_bar:
        imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)

        # Save peek images every 100 images (only if PEEK is enabled)
        if PEEK:
            global_image_counter += imgs.size(0)  # Add batch size to counter
            if global_image_counter >= 1000:
                # Save the first image from this batch
                peek_img = imgs[0].cpu()  # Get first image and move to CPU
                class_name = CLASS_NAMES[labels[0].item()]
                
                # Save with informative filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"epoch{epoch:02d}_{timestamp}_{class_name}.png"
                save_path = os.path.join(PEEK_DIR, filename)
                
                # Convert tensor to PIL image and save
                vutils.save_image(peek_img, save_path, normalize=True)
                
                # Reset counter
                global_image_counter = 0

        optimizer.zero_grad()
        outputs = model(imgs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        train_loss += loss.item()
        progress_bar.set_postfix(loss=loss.item())

    # Validation
    model.eval()
    correct = 0
    total = 0

    with torch.no_grad():
        for imgs, labels in test_loader:
            imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
            outputs = model(imgs)
            _, predicted = torch.max(outputs, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

    val_acc = correct / total

    print(f"Epoch {epoch}/{EPOCHS} | "
          f"Train Loss: {train_loss/len(train_loader):.4f} | "
          f"Test Acc: {val_acc*100:.2f}%")

    # Save best model
    if val_acc >= best_acc:
        best_acc = val_acc
        torch.save(model.state_dict(), "best_model.pth")
        print(f"✔ Best model updated! (Acc: {val_acc*100:.2f}%)")

print("Training complete. Best accuracy =", best_acc*100, "%")
