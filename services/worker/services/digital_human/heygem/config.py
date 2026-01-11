"""
Configuration and constants for HeyGem Inference Engine.
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
LIBS_DIR = BASE_DIR / "libs"
MODELS_DIR = BASE_DIR / "models"

# Ensure directories exist
os.makedirs(LIBS_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

# Model filenames (expected to be in MODELS_DIR)
CHECKPOINT_PATH = MODELS_DIR / "heygem_checkpoint.pth"
FACE_DETECTOR_PATH = MODELS_DIR / "face_detector.onnx"

# Inference settings
BATCH_SIZE = 1  # Adjust based on VRAM
USE_FP16 = True
DEVICE = "cuda" # or "cpu"
