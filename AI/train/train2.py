import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from datetime import datetime
from tqdm.auto import tqdm

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

DATA_DIR = "../data"   # Resized dataset

AUG_MODE = 1
# 0 = NO augmentation (only resize + normalize)
# 1 = Minimal augmentation (recommended)
# 2 = Strong augmentation

BATCH_SIZE = 32
LR = 0.0005
EPOCHS = 25
IMG_SIZE = 100

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


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
            transforms.ColorJitter(brightness=0.2, contrast=0.2),
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

best_acc = 0.0

for epoch in range(1, EPOCHS + 1):
    model.train()
    train_loss = 0

    print(f"\nEpoch {epoch}/{EPOCHS}")
    progress_bar = tqdm(train_loader, desc="Training", leave=False)

    for imgs, labels in progress_bar:
        imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)

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
    if val_acc > best_acc:
        best_acc = val_acc
        torch.save(model.state_dict(), "best_model.pth")
        print(f"✔ Best model updated! (Acc: {val_acc*100:.2f}%)")

print("Training complete. Best accuracy =", best_acc*100, "%")
