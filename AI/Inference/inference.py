# inference.py
import os
import time
import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image

# ------------------ CONFIG ------------------
IMG_SIZE = 100
MODEL_FILE = "model_small.pth"  # assumes model is in the same folder
CLASS_NAMES = ['black', 'empty', 'white']  # same order as training

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ------------------ MODEL DEFINITION ------------------
class ChessCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1), nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(),
            nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 12 * 12, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, len(CLASS_NAMES))
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x

# ------------------ FUNCTION FOR INFERENCE ------------------
def predict_image(image_path, model_path=MODEL_FILE):
    """
    Predict the class of a chess square image.
    Returns a list of tuples: [(class_name, confidence), ...] sorted by confidence descending.
    """
    # Load image
    img = Image.open(image_path).convert("RGB")
    transform = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor()
    ])
    img_tensor = transform(img).unsqueeze(0).to(DEVICE)  # add batch dim

    # Load model
    model = ChessCNN().to(DEVICE)
    model.load_state_dict(torch.load(model_path, map_location=DEVICE))
    model.eval()

    # Inference
    start_time = time.time()
    with torch.no_grad():
        output = model(img_tensor)
        probs = torch.softmax(output, dim=1).squeeze().cpu().tolist()
    elapsed_time = time.time() - start_time

    # Pair with class names and sort
    results = list(zip(CLASS_NAMES, probs))
    results.sort(key=lambda x: x[1], reverse=True)
    return results, elapsed_time

# ------------------ STANDALONE EXECUTION ------------------
if __name__ == "__main__":
    # Find image.jpg or image.png in current folder
    for fname in ["image.jpg", "image.png"]:
        if os.path.exists(fname):
            image_file = fname
            break
    else:
        print("No image.jpg or image.png found in current folder.")
        exit()

    # Run prediction
    predictions, elapsed = predict_image(image_file)
    print(f"Predictions for {image_file}:")
    for cls, conf in predictions:
        print(f"  {cls}: {conf*100:.2f}%")
    print(f"Inference time: {elapsed*1000:.2f} ms")
