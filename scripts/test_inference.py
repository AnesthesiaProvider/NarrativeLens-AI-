import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.ml.model_manager import model_manager

print(f"Device: {model_manager.device_str}", flush=True)
loaded = model_manager.load_model("hate_speech")
print(f"Hate speech loaded: {loaded}", flush=True)
meta = model_manager._model_metadata["hate_speech"]
print(f"Model ID loaded: {meta['model_id']}", flush=True)

samples = [
    ("Hello world, have a wonderful and peaceful day!", "Normal"),
    ("You are such an absolute idiot and stupid moron, get lost.", "Offensive"),
    ("All immigrants are vermin and parasites, we must eradicate them.", "Hate Speech"),
    ("Yeh log desh ke dushman hain inko maar do", "Hinglish Hate Speech")
]

for text, desc in samples:
    res = model_manager.predict_hate_speech(text, explain=True)
    print(f"\n--- {desc} ---", flush=True)
    print(f"Input: {text}", flush=True)
    print(f"Prediction: {res['predicted_label']} (conf: {res['confidence']:.4f})", flush=True)
    print(f"Probabilities: {res['class_probabilities']}", flush=True)
    if res.get("explanation") and "top_features" in res["explanation"]:
        print(f"Top features: {res['explanation']['top_features'][:3]}", flush=True)
