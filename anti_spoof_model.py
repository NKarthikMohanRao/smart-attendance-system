"""
Model-based face anti-spoofing using pretrained ONNX models
(e.g. Silent-Face-Anti-Spoofing MiniFASNet).

Loads the ONNX model once at startup and evaluates face crops for liveness,
returning a 0-1 real-face confidence score. Falls back gracefully to the
heuristic texture_liveness_score if the model file is missing or fails.
"""

import os
import cv2
import numpy as np
import config

try:
    import onnxruntime as ort
    _ONNX_AVAILABLE = True
except ImportError:
    _ONNX_AVAILABLE = False

# Global state for one-time model loading and warning deduplication
_MODEL_SESSION = None
_MODEL_LOAD_ATTEMPTED = False
_WARNING_PRINTED = False


def _print_fallback_warning_once(reason):
    global _WARNING_PRINTED
    if not _WARNING_PRINTED:
        print(f"[WARNING] Anti-spoofing model unavailable ({reason}). "
              f"Falling back to heuristic texture_liveness_score.")
        _WARNING_PRINTED = True


def reset_model_session():
    """Resets global cached model session (useful for testing or reloading)."""
    global _MODEL_SESSION, _MODEL_LOAD_ATTEMPTED, _WARNING_PRINTED
    _MODEL_SESSION = None
    _MODEL_LOAD_ATTEMPTED = False
    _WARNING_PRINTED = False


def get_model_session():
    """Loads the ONNX runtime InferenceSession once at startup."""
    global _MODEL_SESSION, _MODEL_LOAD_ATTEMPTED
    if _MODEL_LOAD_ATTEMPTED:
        return _MODEL_SESSION

    _MODEL_LOAD_ATTEMPTED = True

    if not _ONNX_AVAILABLE:
        _print_fallback_warning_once("onnxruntime package not installed")
        return None

    model_path = getattr(config, "ANTI_SPOOF_MODEL_PATH", "models/MiniFASNetV2.onnx")
    if not os.path.exists(model_path):
        _print_fallback_warning_once(f"model file missing at '{model_path}'")
        return None

    try:
        # Suppress ONNX runtime verbose warnings
        so = ort.SessionOptions()
        so.log_severity_level = 3
        _MODEL_SESSION = ort.InferenceSession(model_path, so)
    except Exception as e:
        _print_fallback_warning_once(f"failed to load ONNX model: {e}")
        _MODEL_SESSION = None

    return _MODEL_SESSION


def model_based_liveness_score(face_bgr, fallback_fn=None):
    """
    Evaluates face crop liveness using the pretrained ONNX model.
    
    Args:
        face_bgr: BGR numpy image of the cropped face region.
        fallback_fn: Function to call if model is unavailable or inference fails.
                     Defaults to liveness.texture_liveness_score.
                     
    Returns:
        float: 0.0 to 1.0 confidence score where 1.0 is a real live face.
    """
    if fallback_fn is None:
        from liveness import texture_liveness_score
        fallback_fn = texture_liveness_score

    if face_bgr is None or face_bgr.size == 0:
        return 0.0

    session = get_model_session()
    if session is None:
        return float(fallback_fn(face_bgr))

    try:
        # Inspect model expected input shape (default to 80x80 for MiniFASNet)
        input_info = session.get_inputs()[0]
        input_name = input_info.name
        shape = input_info.shape
        height = shape[2] if len(shape) >= 4 and isinstance(shape[2], int) else 80
        width = shape[3] if len(shape) >= 4 and isinstance(shape[3], int) else 80

        # Preprocess face crop: resize, normalize to [0, 1], transpose HWC->CHW, add batch dim
        resized = cv2.resize(face_bgr, (width, height))
        img_float = resized.astype(np.float32) / 255.0
        img_chw = np.transpose(img_float, (2, 0, 1))
        img_batch = np.expand_dims(img_chw, axis=0)

        # Inference
        outputs = session.run(None, {input_name: img_batch})
        logits = np.array(outputs[0]).flatten()

        # Compute softmax probabilities
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / np.sum(exp_logits)

        # In Silent-Face-Anti-Spoofing MiniFASNet models (3 classes):
        # Index 0: print attack, Index 1: live face, Index 2: replay attack
        # In 2-class models: Index 0: spoof, Index 1: live
        if len(probs) >= 2:
            return float(probs[1])
        return float(probs[0])
    except Exception as e:
        _print_fallback_warning_once(f"inference error ({e})")
        return float(fallback_fn(face_bgr))
