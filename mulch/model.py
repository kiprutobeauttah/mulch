import base64
import io
import os
import sys
import time
import uuid

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from torchvision import models, transforms

try:
    from torchvision.transforms import InterpolationMode
    _RESIZE = transforms.Resize((224, 224), interpolation=InterpolationMode.BILINEAR)
except Exception:
    _RESIZE = transforms.Resize((224, 224))

if getattr(sys, "frozen", False):
    RESOURCE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
else:
    RESOURCE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODEL_REGISTRY = {
    "frozen_backbone": {
        "path": os.path.join(RESOURCE_DIR, "models", "densenet121_frozen-backbone.zip"),
        "label": "DenseNet121 · Frozen backbone (best F1)",
        "note": "Best validation F1 during training",
    },
    "epoch3": {
        "path": os.path.join(RESOURCE_DIR, "models", "densenet121_epoch-3.zip"),
        "label": "DenseNet121 · Epoch 3",
        "note": "Snapshot saved at epoch 3",
    },
}

CLASS_NAMES = ["NORMAL", "PNEUMONIA"]

_MEAN = [0.485, 0.456, 0.406]
_STD = [0.229, 0.224, 0.225]

TRANSFORM = transforms.Compose([
    _RESIZE,
    transforms.ToTensor(),
    transforms.Normalize(mean=_MEAN, std=_STD),
])

MODELS = {}

_activations = None
_gradients = None


def _forward_hook(_module, _input, output):
    global _activations
    _activations = output


def _backward_hook(_module, _grad_input, grad_output):
    global _gradients
    _gradients = grad_output[0]


def build_model():
    model = models.densenet121(weights=None)
    num_features = model.classifier.in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.4),
        nn.Linear(num_features, len(CLASS_NAMES)),
    )

    def safe_forward(x):
        features = model.features(x).clone()
        out = F.relu(features, inplace=True)
        out = F.adaptive_avg_pool2d(out, (1, 1))
        out = torch.flatten(out, 1)
        out = model.classifier(out)
        return out

    model.forward = safe_forward
    model.eval()
    return model


def load_models():
    missing = [info["path"] for info in MODEL_REGISTRY.values()
               if not os.path.exists(info["path"])]
    if missing:
        raise FileNotFoundError(f"Model weights not found: {missing}")
    for key, info in MODEL_REGISTRY.items():
        model = build_model()
        state = torch.load(info["path"], map_location="cpu")
        model.load_state_dict(state, strict=True)
        model.eval()
        MODELS[key] = model


def _load_image(file_bytes: bytes) -> Image.Image:
    return Image.open(io.BytesIO(file_bytes)).convert("RGB")


def confidence_level(confidence: float) -> str:
    if confidence >= 0.90:
        return "high"
    if confidence >= 0.70:
        return "medium"
    return "low"


def interpretation(verdict: str, level: str) -> str:
    if verdict == "PNEUMONIA":
        if level == "high":
            return ("High-confidence automated finding of pneumonia-compatible "
                    "lung opacity. Review the highlighted regions and correlate "
                    "with clinical signs before treatment decisions.")
        if level == "medium":
            return ("Moderate-confidence finding. Lung opacity compatible with "
                    "pneumonia may be present; consider repeat imaging or "
                    "correlation with clinical and laboratory findings.")
        return ("Low-confidence finding. Automated pattern is inconclusive- "
                "exercise caution and weigh the full radiograph and patient "
                "context before any clinical decision.")
    if level == "high":
        return ("High-confidence finding of no pneumonia-compatible opacity. "
                "Still interpret alongside the full study and clinical "
                "presentation.")
    if level == "medium":
        return ("Moderate-confidence normal reading. Some uncertainty remains- "
                "interpret in the light of the entire radiograph.")
    return ("Low-confidence normal reading. Automated pattern is inconclusive- "
            "verify manually and correlate with clinical findings.")


def _jet_lut() -> np.ndarray:
    n = 256
    t = np.linspace(0, 1, n)
    points = np.array([
        (0.000, 0.000, 0.400),
        (0.125, 0.000, 0.800),
        (0.300, 0.300, 1.000),
        (0.500, 1.000, 1.000),
        (0.700, 1.000, 1.000),
        (0.800, 1.000, 0.500),
        (0.900, 1.000, 0.000),
        (1.000, 0.600, 0.000),
    ])
    pos = points[:, 0]
    lut = np.zeros((n, 3))
    for c in range(3):
        lut[:, c] = np.interp(t, pos, points[:, c])
    return (lut * 255.0).astype(np.uint8)


_JET = _jet_lut()


def _heatmap_images(cam: np.ndarray, original: Image.Image):
    cam_norm = np.clip(cam, 0.0, 1.0)
    cam_norm = cam_norm - cam_norm.min()
    denom = cam_norm.max() or 1.0
    cam_norm = cam_norm / denom

    cam_resized = np.array(Image.fromarray(
        _JET[(np.round(cam_norm * 255).astype(np.uint8))]).resize(original.size, Image.BICUBIC)
    )

    alone = Image.fromarray(cam_resized)

    heat_rgba = Image.fromarray(cam_resized).convert("RGBA")
    alpha = Image.fromarray(
        (cam_norm * 255).astype(np.uint8)
    ).resize(original.size, Image.BICUBIC).convert("L")
    heat_rgba.putalpha(alpha)

    base = original.convert("RGBA")
    overlay = Image.alpha_composite(base, heat_rgba).convert("RGB")

    return _png_data_url(overlay), _png_data_url(alone)


def _png_data_url(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _gradcam(model, tensor):
    handle_fwd = model.features.register_forward_hook(_forward_hook)
    handle_bwd = model.features.register_full_backward_hook(_backward_hook)

    global _activations, _gradients
    _activations = _gradients = None

    logits = None
    cam_map = None
    try:
        with torch.enable_grad():
            tensor.requires_grad_(True)
            logits = model(tensor)
            pred = logits.argmax(dim=1)
            one_hot = torch.zeros_like(logits)
            one_hot.scatter_(1, pred.unsqueeze(1), 1.0)
            logits.backward(gradient=one_hot)

        if _activations is not None and _gradients is not None:
            weights = _gradients.mean(dim=(2, 3), keepdim=True)
            cam = torch.relu((weights * _activations).sum(dim=1, keepdim=True))
            cam = F.interpolate(cam, size=(224, 224), mode="bilinear", align_corners=False)
            cam_map = cam[0, 0].detach().cpu().numpy()
    finally:
        handle_fwd.remove()
        handle_bwd.remove()
        _activations = _gradients = None

    return logits, cam_map


@torch.no_grad()
def predict(file_bytes: bytes, model_key: str):
    model = MODELS[model_key]
    img = _load_image(file_bytes)
    tensor = TRANSFORM(img).unsqueeze(0)
    logits = model(tensor)
    probs = torch.softmax(logits, dim=1)[0]
    prob_normal = float(probs[0].item())
    prob_pneumonia = float(probs[1].item())
    verdict_idx = 0 if prob_normal >= prob_pneumonia else 1
    return {
        "image_id": uuid.uuid4().hex[:8],
        "model": model_key,
        "probabilities": {
            "NORMAL": prob_normal,
            "PNEUMONIA": prob_pneumonia,
        },
        "verdict": CLASS_NAMES[verdict_idx],
        "verdict_index": verdict_idx,
        "confidence": max(prob_normal, prob_pneumonia),
    }


def analyze(file_bytes: bytes, model_key: str) -> dict:
    started = time.perf_counter()
    result = predict(file_bytes, model_key)
    model = MODELS[model_key]
    img = _load_image(file_bytes)
    tensor = TRANSFORM(img).unsqueeze(0)

    attention = None
    heatmap = None
    try:
        _logits, cam_map = _gradcam(model, tensor)
        if cam_map is not None:
            attention, heatmap = _heatmap_images(cam_map, img)
    except Exception:
        pass

    result["confidence_level"] = confidence_level(result["confidence"])
    result["interpretation"] = interpretation(
        result["verdict"], result["confidence_level"])
    result["attention"] = attention
    result["heatmap"] = heatmap
    result["latency_ms"] = round((time.perf_counter() - started) * 1000)
    return result