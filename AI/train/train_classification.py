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

DATA_DIR = "../data"
PEEK = True                 # <<< ENABLE / DISABLE PEEK
PEEK_EVERY = 1000           # Save one image every N samples
AUG_MODE = 1                # Keep mode 1

BATCH_SIZE = 32
LR = 0.001                  # Slightly higher LR for faster convergence
EPOCHS = 40                 # More epochs with early stopping
IMG_SIZE = 32               # Reduced from 100 - sufficient for piece detection
EARLY_STOP_PATIENCE = 8     # Stop if no improvement for 8 epochs

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ------------------------------------------------------------
# CUSTOM TRANSFORMS (WHITE-ON-WHITE ROBUST)
# ------------------------------------------------------------

class RandomLowContrast:
    """Simulate bad lighting without unrealistic artifacts."""
    def __init__(self, p=0.4):
        self.p = p

    def __call__(self, img):
        if random.random() < self.p:
            factor = random.uniform(0.6, 0.9)
            return transforms.functional.adjust_contrast(img, factor)
        return img


class RandomGrayscaleSoft:
    """Force edge learning by sometimes removing color."""
    def __init__(self, p=0.25):
        self.p = p

    def __call__(self, img):
        if random.random() < self.p:
            return transforms.functional.to_grayscale(img, num_output_channels=3)
        return img


# ------------------------------------------------------------
# AUGMENTATION PIPELINES
# ------------------------------------------------------------

def get_transforms():
    train_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.RandomRotation(8),
        transforms.ColorJitter(brightness=0.4, contrast=0.2),
        RandomLowContrast(p=0.4),
        RandomGrayscaleSoft(p=0.25),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
    ])

    test_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
    ])

    return train_tf, test_tf


train_tf, test_tf = get_transforms()

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
# CLASS WEIGHTS (WHITE-ON-WHITE FIX)
# ------------------------------------------------------------
# Expected order: ['black', 'empty', 'white']
class_weights = torch.tensor([1.0, 1.2, 1.6], device=DEVICE)

# ------------------------------------------------------------
# CNN MODEL (LIGHTWEIGHT - NO OVERFITTING)
# ------------------------------------------------------------
# For 32x32 input: 32 -> 16 -> 8 -> 4 after 3 max pools
# Much simpler architecture for simple color+presence detection

class ChessCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            # Layer 1: 32x32 -> 16x16
            nn.Conv2d(3, 8, 3, padding=1),
            nn.BatchNorm2d(8),
            nn.ReLU(),
            nn.MaxPool2d(2),

            # Layer 2: 16x16 -> 8x8
            nn.Conv2d(8, 16, 3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d(2),

            # Layer 3: 8x8 -> 4x4
            nn.Conv2d(16, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2),
        )

        # Much smaller classifier: 512 -> 32 -> 3
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(32 * 4 * 4, 32),  # 512 -> 32
            nn.ReLU(),
            nn.Dropout(0.2),  # Lower dropout
            nn.Linear(32, 3)
        )

    def forward(self, x):
        return self.classifier(self.features(x))


model = ChessCNN().to(DEVICE)

criterion = nn.CrossEntropyLoss(weight=class_weights)
optimizer = optim.Adam(model.parameters(), lr=LR, weight_decay=1e-4)  # L2 regularization
scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=4)

# ------------------------------------------------------------
# PEEK SETUP
# ------------------------------------------------------------

PEEK_DIR = "peek"
os.makedirs(PEEK_DIR, exist_ok=True)
global_image_counter = 0

# ------------------------------------------------------------
# TRAINING + VALIDATION LOOP (WITH EARLY STOPPING)
# ------------------------------------------------------------

if __name__ == "__main__":
    best_acc = 0.0
    patience_counter = 0

    for epoch in range(1, EPOCHS + 1):
        model.train()
        train_loss = 0.0

        print(f"\nEpoch {epoch}/{EPOCHS}")
        progress_bar = tqdm(train_loader, desc="Training", leave=False)

        for imgs, labels in progress_bar:
            imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)

            # ---------------- PEEK LOGIC ----------------
            if PEEK:
                global_image_counter += imgs.size(0)
                if global_image_counter >= PEEK_EVERY:
                    img = imgs[0].cpu()
                    label = CLASS_NAMES[labels[0].item()]
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"epoch{epoch:02d}_{timestamp}_{label}.png"
                    vutils.save_image(img, os.path.join(PEEK_DIR, filename), normalize=True)
                    global_image_counter = 0
            # --------------------------------------------

            optimizer.zero_grad()
            outputs = model(imgs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            train_loss += loss.item()
            progress_bar.set_postfix(loss=loss.item())

        # ---------------- VALIDATION ----------------
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

        print(
            f"Epoch {epoch} | "
            f"Train Loss: {train_loss/len(train_loader):.4f} | "
            f"Test Acc: {val_acc*100:.2f}%"
        )

        # Update learning rate based on validation accuracy
        scheduler.step(val_acc)
        
        # Early stopping + model saving
        if val_acc > best_acc:
            best_acc = val_acc
            patience_counter = 0
            torch.save(model.state_dict(), "best_model.pth")
            print(f"✔ Best model updated! ({val_acc*100:.2f}%)")
        else:
            patience_counter += 1
            print(f"No improvement ({patience_counter}/{EARLY_STOP_PATIENCE})")
            
        if patience_counter >= EARLY_STOP_PATIENCE:
            print(f"\nEarly stopping triggered after {epoch} epochs")
            break

    print(f"\n{'='*50}")
    print(f"Training complete!")
    print(f"Best validation accuracy: {best_acc*100:.2f}%")
    print(f"Model saved as: best_model.pth")
    print(f"{'='*50}")
