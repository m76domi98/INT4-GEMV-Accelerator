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

Python 3.12 is required. The pinned torch 2.5.1 has no Python 3.14 build, so a newer default Python will fail to install. A simulator is also needed: Icarus Verilog is the default, and Verilator also works (`make test SIM=verilator`). Icarus is tested on Linux (WSL).

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
| `make export` | Exports weights and activations | Stage 1 (not implemented) |
| `make results` | Regenerates tables, plots, and logs | Stage 6 (not implemented) |
