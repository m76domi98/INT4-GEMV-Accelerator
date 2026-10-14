"""Stage 4 results table: variant A (per-channel output scale) vs. B (per-tensor output scale, same weights).

Error and saturation numbers come from the same evaluate() as make golden. Cycles come from the layer sim logs,
results/stage4_layer_pc.log and results/stage4_layer_iso.log (make test-layer, make test-layer-iso, tee'd there).
Writes results/stage4_variants.md and prints it.
"""
import os
import re

import numpy as np

from check_golden import NPZ_PATH, SPLITS, evaluate

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
CYCLES_RE = re.compile(r"compute (\d+) load (\d+)")
VARIANTS = (("A per-channel", "pc", "pc"), ("B per-tensor out", "pc", "iso"))  # (label, weight tag, output tag)


def sim_cycles(tag: str) -> tuple[int, int]:
    """(compute, load) cycles from the first run in the variant's sim log. Fails loudly if the log is missing."""
    with open(os.path.join(RESULTS_DIR, f"stage4_layer_{tag}.log")) as f:
        found = CYCLES_RE.search(f.read())
    assert found, f"no 'compute N load M' line in stage4_layer_{tag}.log, run the sim first"
    return int(found.group(1)), int(found.group(2))


def main() -> None:
    data = np.load(NPZ_PATH)
    m_iso = data["m_iso"]
    assert m_iso.min() >= -(1 << 15) and m_iso.max() < (1 << 15), "m_iso does not fit m_mem"
    lines = [
        "| Variant | Split | Compute cycles | Load cycles | Max abs err | RMSE | Saturations |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for label, w_tag, o_tag in VARIANTS:
        res = evaluate(data, w_tag, o_tag)
        compute, load = sim_cycles(o_tag)
        for split in SPLITS:
            err = res[split]["err"]
            lines.append(
                f"| {label} | {split} | {compute} | {load} | {err.max():.4f} | "
                f"{np.sqrt(np.mean(err**2)):.4f} | {res[split]['sats']} |"
            )
    lines.append(f"\nm_iso range {m_iso.min()}..{m_iso.max()}, m_pc range {data['m_pc'].min()}..{data['m_pc'].max()}")
    out = "\n".join(lines)
    with open(os.path.join(RESULTS_DIR, "stage4_variants.md"), "w") as f:
        f.write(out + "\n")
    print(out)


if __name__ == "__main__":
    main()
