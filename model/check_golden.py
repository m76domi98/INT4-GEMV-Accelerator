"""Stage 1 golden check (spec 01): integer golden model vs. float reference.

Reads export/out/ (make export). Prints the numbers for the spec's Results and
Predictions sections. Float math here is the reference and the bound only.
The datapath is golden.gemv_int.
"""
import json
import os

import numpy as np

from golden import gemv_int

EXPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "export", "out")
NPZ_PATH = os.path.join(EXPORT_DIR, "layer15_up_proj.npz")
MANIFEST_PATH = os.path.join(EXPORT_DIR, "manifest.json")

ACC_SPEC_LIMIT = 2**20  # spec 01: accumulator budget for |acc|
ACC_P3_LIMIT = 2**17  # prediction P3: 18-bit signed
SPLITS = ("cal", "test")


def run_golden(q: np.ndarray, m: np.ndarray, x_int: np.ndarray) -> tuple[np.ndarray, int, int]:
    """Golden outputs for each row of x_int. Returns (y_int, max_abs_acc, saturations)."""
    q_rows = q.tolist()  # same weights for every vector, so convert once instead of per call
    m_rows = m.tolist()
    y_all = []
    max_acc = 0  # running max across all vectors, not just the last one
    saturations = 0
    for x_row in x_int.tolist():  # only x changes between calls, weights stay put
        y, acc, sat = gemv_int(q_rows, x_row, m_rows)
        y_all.append(y)
        max_acc = max(max_acc, acc)
        saturations += sat
    return np.array(y_all, dtype=np.float64), max_acc, saturations


def frozen_bound(x_hat: np.ndarray, w_hat: np.ndarray, s_x: float, s_r: np.ndarray, s_out: np.ndarray) -> np.ndarray:
    """E_r from spec 01, per vector (rows of x_hat) and per output row. Shape (n, R)."""
    e_w = np.abs(x_hat).sum(axis=1)[:, None] * (s_r / 2)[None, :]  # weight rounding: half a weight step, times the |x| sum
    e_x = (s_x / 2) * np.abs(w_hat).sum(axis=1)  # activation rounding: half an act step, times the |w| sum
    e_rq = s_out / 2  # final requant rounding, half an output step, same for every vector
    return e_w + e_x[None, :] + e_rq[None, :]  # worst case: all three errors line up and add


def rms_form(x_hat: np.ndarray, w_hat: np.ndarray, s_x: float, s_r: np.ndarray, s_out: np.ndarray, k: int) -> np.ndarray:
    """Predicted error standard deviation from spec 01 (RMS form). Shape (n, R)."""
    rms_x = np.sqrt(np.mean(x_hat**2, axis=1))  # typical activation size per vector
    rms_w = np.sqrt(np.mean(w_hat**2, axis=1))  # typical weight size per row
    # uniform rounding error has variance step^2/12, and k of them add up, hence sqrt(k/12)
    sigma_w = s_r[None, :] * np.sqrt(k / 12) * rms_x[:, None]
    sigma_x = s_x * np.sqrt(k / 12) * rms_w[None, :]
    sigma_rq = (s_out / np.sqrt(12))[None, :]  # one rounding error, no k term
    return np.sqrt(sigma_w**2 + sigma_x**2 + sigma_rq**2)  # independent errors, so add variances then sqrt


def multiplier_term(x_int: np.ndarray, q: np.ndarray, s_x: float, s_r: np.ndarray, s_out: np.ndarray, m: np.ndarray) -> np.ndarray:
    """Error from rounding M_r. Not in the frozen E_r. Shape (n, R).

    Golden dequantized output is acc * M_r / 2^15 * s_out. The exact value is acc * s_x * s_r.
    Their difference is |acc| * |M_r - M_true| / 2^15 * s_out.
    """
    acc = x_int.astype(np.int64) @ q.astype(np.int64).T  # redo the int dot products here, int64 so nothing overflows
    m_true = s_x * s_r / s_out * 2**15  # the multiplier we'd want if it didn't have to be an integer
    return np.abs(acc) * np.abs(m - m_true)[None, :] / 2**15 * s_out[None, :]  # error grows with |acc| and how far M is off


def evaluate(data: np.lib.npyio.NpzFile, tag: str) -> dict:
    """Golden vs. float for one quantization variant ('pc' or 'pt'), per split."""
    q = data[f"q_{tag}"]
    s_r = data[f"s_r_{tag}"]
    s_out = data[f"s_out_{tag}"]
    m = data[f"m_{tag}"]
    s_x = float(data["s_x"])
    w = data["w_float"]
    w_hat = q * s_r[:, None]  # weights as the golden actually sees them after quantizing
    k = w.shape[1]  # inner dim, 576 for up_proj
    result = {"w_max": np.abs(w).max(axis=1)}  # kept for the P1 correlation later
    for split in SPLITS:
        x = data[f"x_{split}"]  # float activations, the reference
        x_int = data[f"x_{split}_int"]
        y_int, max_acc, sats = run_golden(q, m, x_int)
        err = np.abs(y_int * s_out[None, :] - x @ w.T)  # golden output (back to float) vs the real float answer
        x_hat = x_int * s_x  # quantized activations as floats, so the bounds use what the golden used
        bound = frozen_bound(x_hat, w_hat, s_x, s_r, s_out)
        m_term = multiplier_term(x_int, q, s_x, s_r, s_out, m)
        result[split] = {
            "err": err,
            "bound": bound,
            "bound_with_m": bound + m_term,
            "sigma": rms_form(x_hat, w_hat, s_x, s_r, s_out, k),
            "max_acc": max_acc,
            "sats": sats,
            "m_term_max": float(m_term.max()),
        }
    return result


def print_variant(name: str, res: dict, manifest: dict) -> None:
    print(f"\n== {name} ==")
    for split in SPLITS:
        r = res[split]
        err, bound = r["err"], r["bound"]
        clip = manifest[f"act_clip_{split}"]
        print(f"[{split}] vectors={err.shape[0]} rows={err.shape[1]}")
        print(f"  max abs err      {err.max():.6g}")
        print(f"  RMSE             {np.sqrt(np.mean(err**2)):.6g}")
        print(f"  E_r min/med/max  {bound.min():.6g} / {np.median(bound):.6g} / {bound.max():.6g}")
        print(f"  E_r violations   {int(np.count_nonzero(err > bound))} (min margin {np.min(bound - err):.6g})")
        print(f"  violations w/ M  {int(np.count_nonzero(err > r['bound_with_m']))} (M-term max {r['m_term_max']:.6g})")
        print(f"  max |acc|        {r['max_acc']} ({r['max_acc'] / ACC_SPEC_LIMIT:.3f} of 2^20)")
        print(f"  requant sats     {r['sats']}; activation clips {clip}")


def print_predictions(pc: dict, pt: dict) -> None:
    print("\n== Predictions ==")
    err_pc = np.concatenate([pc[s]["err"] for s in SPLITS])
    err_pt = np.concatenate([pt[s]["err"] for s in SPLITS])
    print(f"P1 max abs err: per-channel {err_pc.max():.6g} vs per-tensor {err_pt.max():.6g} -> "
          f"{'PASS' if err_pc.max() <= err_pt.max() else 'FAIL'}")
    gap_row = err_pt.mean(axis=0) - err_pc.mean(axis=0)  # per row: how much worse per-tensor is than per-channel
    corr = np.corrcoef(gap_row, pc["w_max"])[0, 1]  # do rows with big weights get more help from per-channel?
    print(f"P1 (gap vs max|w_r|, predicted negative): corr = {corr:.3f}")

    # P2: per vector, compare max over rows against the worst-case bound and the RMS form.
    measured = np.concatenate([pc[s]["err"] for s in SPLITS]).max(axis=1)  # worst row's error, per vector
    worst = np.concatenate([pc[s]["bound"] for s in SPLITS]).max(axis=1)  # worst row's bound, per vector
    rms = np.concatenate([pc[s]["sigma"] for s in SPLITS]).max(axis=1)  # same, but the RMS prediction
    all_below = bool(np.all(measured < worst))
    closer_to_rms = bool(np.mean(np.abs(measured - rms)) < np.mean(np.abs(measured - worst)))
    print(f"P2 max err below worst-case E_r on every vector: {'PASS' if all_below else 'FAIL'}")
    print(f"P2 closer to RMS form than worst case (mean |meas-RMS| {np.mean(np.abs(measured - rms)):.6g}"
          f" vs mean |meas-worst| {np.mean(np.abs(measured - worst)):.6g}): "
          f"{'PASS' if closer_to_rms else 'FAIL'}")

    acc_cal = pc["cal"]["max_acc"]
    print(f"P3 real-weight max |acc| on calibration {acc_cal} vs 2^17 = {ACC_P3_LIMIT}: "
          f"{'PASS' if acc_cal < ACC_P3_LIMIT else 'FAIL'}")
    print(f"P3 test-set max |acc| {pc['test']['max_acc']}")


def main() -> None:
    data = np.load(NPZ_PATH)  # arrays written by export_layer.py
    with open(MANIFEST_PATH, encoding="utf-8") as handle:
        manifest = json.load(handle)  # scales/clip counts and the model revision
    pc = evaluate(data, "pc")  # per-channel is the chosen design
    pt = evaluate(data, "pt")  # per-tensor is the thing we compare against
    print(f"layer {manifest['layer']} revision {manifest['model_revision']} s_x {manifest['s_x']:.6g}")
    print_variant("per-channel (chosen)", pc, manifest)
    print_variant("per-tensor (comparison)", pt, manifest)
    print_predictions(pc, pt)


if __name__ == "__main__":
    main()
