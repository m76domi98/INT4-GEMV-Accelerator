"""Versioned export of SmolLM2-135M layers.15.mlp.up_proj (Stage 1, FR2).

Writes export/out/layer15_up_proj.npz and export/out/manifest.json. Run: make export.
Float math lives here. The golden model in model/ reads only the integer arrays
and scales this script writes.
"""
import json
import os

import numpy as np
import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer

SCRIPT_VERSION = "1"
MODEL_ID = "HuggingFaceTB/SmolLM2-135M"
LAYER_INDEX = 15
EXPECTED_SHAPE = (1536, 576)  # (out, in) = (intermediate_size, hidden_size), nn.Linear layout

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
NPZ_PATH = os.path.join(OUT_DIR, "layer15_up_proj.npz")
MANIFEST_PATH = os.path.join(OUT_DIR, "manifest.json")

X_QMAX = 127  # INT8 activation, symmetric
W_QMAX = 7  # INT4 weight, symmetric; datapath keeps [-8, 7]
W_QMIN = -8
Y_QMAX = 127  # INT8 output
REQUANT_SHIFT = 15

# Calibration sets s_x and the output scales. Test prompts are disjoint from them.
CAL_PROMPTS = [
    "The quick brown fox jumps over the lazy dog.",
    "Large language models predict the next token from the tokens before it.",
    "Photosynthesis converts sunlight, water, and carbon dioxide into sugar and oxygen.",
    "The train to the coast leaves at seven in the morning and arrives before noon.",
    "In 1969, astronauts landed on the Moon for the first time.",
    "def add(a, b):\n    return a + b  # add two integers",
    "Once upon a time, a small village sat at the edge of a quiet forest.",
    "Water boils at 100 degrees Celsius at sea level.",
]
TEST_PROMPTS = [
    "Our team reviewed the quarterly budget and agreed to cut two projects.",
    "Mount Everest is the highest mountain above sea level on Earth.",
    "for i in range(10): total += values[i] * weights[i]",
    "Please remember to bring your umbrella if it rains later this afternoon.",
]


def check_known_output() -> None:
    """Hand-computed vector through the weight quantizer (transposed-weight risk)."""
    w = np.array([[0.7, -0.3, 0.0], [-0.14, 0.07, 0.35]])
    x_int = np.array([1, 2, 3])
    q, s_r = quantize_weights(w, per_tensor=False)
    # Hand-computed: s_r = [0.1, 0.05]; q = [[7, -3, 0], [-3, 1, 7]]
    assert q.tolist() == [[7, -3, 0], [-3, 1, 7]], f"weight codes {q.tolist()}"
    assert np.allclose(s_r, [0.1, 0.05]), f"row scales {s_r}"
    # Hand-computed: integer dot products [1, 20]; float dot products [0.1, 1.05]
    y_int = q.astype(np.int64) @ x_int
    assert y_int.tolist() == [1, 20], f"integer dot products {y_int.tolist()}"
    assert np.allclose(s_r * y_int, w @ x_int), "dequantized output off the float reference"
    print("known-output check: pass (q, s_r, dot products match hand computation)")


def load_model() -> tuple[AutoTokenizer, AutoModelForCausalLM]:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype=torch.float32)
    model.eval()
    cfg = model.config
    assert cfg.hidden_size == 576 and cfg.intermediate_size == 1536, (
        f"config dims {cfg.hidden_size}, {cfg.intermediate_size}; spec expects 576, 1536"
    )
    return tokenizer, model


def capture_up_proj_inputs(
    tokenizer: AutoTokenizer, model: AutoModelForCausalLM, prompts: list[str]
) -> np.ndarray:
    """Every token's input to layers.15.mlp.up_proj, shape (tokens, 576)."""
    captured = []
    up_proj = model.model.layers[LAYER_INDEX].mlp.up_proj

    def hook(_module, inputs):
        captured.append(inputs[0][0].detach().double().numpy())

    handle = up_proj.register_forward_pre_hook(hook)
    try:
        with torch.no_grad():
            for prompt in prompts:
                model(**tokenizer(prompt, return_tensors="pt"))
    finally:
        handle.remove()
    return np.concatenate(captured, axis=0)


def quantize_acts(x: np.ndarray, s_x: float) -> np.ndarray:
    return np.clip(np.rint(x / s_x), -X_QMAX, X_QMAX).astype(np.int8)


def quantize_weights(w: np.ndarray, per_tensor: bool) -> tuple[np.ndarray, np.ndarray]:
    """Symmetric INT4. Per output row, or one scale for the whole tensor. Returns (q, s_r)."""
    row_max = np.abs(w).max(axis=1)
    if per_tensor:
        row_max = np.full_like(row_max, np.abs(w).max())
    s_r = row_max / W_QMAX
    q = np.clip(np.rint(w / s_r[:, None]), W_QMIN, W_QMAX).astype(np.int8)
    return q, s_r


def requant_params(
    s_x: float, s_r: np.ndarray, y_cal: np.ndarray, per_tensor: bool
) -> tuple[np.ndarray, np.ndarray]:
    """Output scale per row and fixed-point multiplier M_r = round(s_x * s_r / s_out * 2^15)."""
    row_max_y = np.abs(y_cal).max(axis=0)
    if per_tensor:
        row_max_y = np.full_like(row_max_y, np.abs(y_cal).max())
    s_out = row_max_y / Y_QMAX
    m = np.rint(s_x * s_r / s_out * 2**REQUANT_SHIFT).astype(np.int64)
    return s_out, m


def write_manifest(
    model: AutoModelForCausalLM, s_x: float, x_cal: np.ndarray, x_test: np.ndarray
) -> dict:
    manifest = {
        "script_version": SCRIPT_VERSION,
        "model_id": MODEL_ID,
        "model_revision": getattr(model.config, "_commit_hash", None),
        "layer": f"model.layers.{LAYER_INDEX}.mlp.up_proj",
        "weight_shape": list(EXPECTED_SHAPE),
        "s_x": float(s_x),
        "cal_tokens": int(len(x_cal)),
        "test_tokens": int(len(x_test)),
        "act_clip_cal": int(np.count_nonzero(np.abs(np.rint(x_cal / s_x)) > X_QMAX)),
        "act_clip_test": int(np.count_nonzero(np.abs(np.rint(x_test / s_x)) > X_QMAX)),
        "versions": {
            "numpy": np.__version__,
            "torch": torch.__version__,
            "transformers": transformers.__version__,
        },
    }
    with open(MANIFEST_PATH, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    return manifest


def main() -> None:
    check_known_output()
    tokenizer, model = load_model()
    weight = model.model.layers[LAYER_INDEX].mlp.up_proj.weight.detach().double().numpy()
    assert weight.shape == EXPECTED_SHAPE, f"shape {weight.shape}, expected {EXPECTED_SHAPE}"
    print(f"shape check: pass {weight.shape}")

    x_cal = capture_up_proj_inputs(tokenizer, model, CAL_PROMPTS)
    x_test = capture_up_proj_inputs(tokenizer, model, TEST_PROMPTS)
    s_x = np.abs(x_cal).max() / X_QMAX
    y_cal = x_cal @ weight.T

    arrays = {
        "w_float": weight,
        "s_x": np.float64(s_x),
        "x_cal": x_cal,
        "x_test": x_test,
        "x_cal_int": quantize_acts(x_cal, s_x),
        "x_test_int": quantize_acts(x_test, s_x),
    }
    for tag, per_tensor in (("pc", False), ("pt", True)):
        q, s_r = quantize_weights(weight, per_tensor)
        s_out, m = requant_params(s_x, s_r, y_cal, per_tensor)
        arrays.update({f"q_{tag}": q, f"s_r_{tag}": s_r, f"s_out_{tag}": s_out, f"m_{tag}": m})

    os.makedirs(OUT_DIR, exist_ok=True)
    np.savez(NPZ_PATH, **arrays)
    manifest = write_manifest(model, s_x, x_cal, x_test)
    print(f"wrote {NPZ_PATH}")
    print(f"model revision {manifest['model_revision']}, s_x {manifest['s_x']:.6g}")
    print(f"tokens: cal {manifest['cal_tokens']}, test {manifest['test_tokens']}")


if __name__ == "__main__":
    main()
