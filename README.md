# INT4 GEMV Accelerator Study

Decode-time INT4 GEMV accelerator study. Scope and requirements: [PRD](PRD%20Decode-Time%20INT4%20GEMV%20Accelerator%20Study.md). Stage plan: [docs/PLAN.md](docs/PLAN.md).

## Layout

```
rtl/      SystemVerilog sources
tb/       cocotb testbenches
model/    Python golden model and float reference
export/   weight and activation export scripts
synth/    synthesis scripts and constraints
results/  generated tables, plots, and logs (scripted output only)
docs/     plan, design docs, decision log
```

## Setup

Python 3.12 is required. The pinned torch 2.5.1 has no Python 3.14 build, so a newer default Python will fail to install. A simulator is also needed: Icarus Verilog is the default. `make test SIM=verilator` runs the smoke test under Verilator. The PE and tile targets are Icarus only for now. Icarus is tested on Linux (WSL).

```bash
python3.12 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
make test
```

## Commands

| Command | What it does | Status |
| --- | --- | --- |
| `make test` | Runs the cocotb smoke test | Stage 0 |
| `make export` | Exports the pinned SmolLM2 layer's weights and activations to `export/out/` (needs the model in the Hugging Face cache or network access) | Stage 1 |
| `make golden` | Runs the golden check and writes `results/stage1_golden.log` | Stage 1 |
| `make test-pe` | PE cocotb tests: 84 cases, corner grid, worst case, random, hold | Stage 2, Icarus only |
| `make test-tile` | Tile cocotb tests: random, done and hold, idle gaps between terms, sampled real-layer rows on both splits, missing-`clr` contract. Needs `make export` first | Stage 2, Icarus only |
| `make results` | Regenerates tables, plots, and logs | Stage 6 (not implemented) |

### Full regression

Run from a clean checkout, in this order:

```bash
make export       # only if export/out/ is missing; the .npz is git-ignored
make golden
make test
make test-pe
make test-tile
```

`make export` fetches or reads the model at the revision pinned in `export/export_layer.py`. `make test-tile` reads `export/out/layer15_up_proj.npz`, so it needs the export first.
