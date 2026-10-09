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

Python 3.11 or newer, plus a simulator. Icarus Verilog is the default; Verilator also works (`make test SIM=verilator`).

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Commands

| Command | What it does | Status |
| --- | --- | --- |
| `make test` | Runs the cocotb smoke test | Stage 0 |
| `make export` | Exports weights and activations | Stage 1 (not implemented) |
| `make results` | Regenerates tables, plots, and logs | Stage 6 (not implemented) |
