# Stage 0: Setup

**Status:** Done (2026-10-10) · **Weeks:** Setup (before Week 1) · **Depends on:** PRD Draft v1
**Exit criterion:** A clean checkout runs the test command and the export command, both with no manual steps.

## Goal

Make the repo reproducible before any design work starts. PRD §9 requires one command to rerun simulation and regenerate the results table from a clean checkout.

## Inputs

- [PRD](../../PRD%20Decode-Time%20INT4%20GEMV%20Accelerator%20Study.md) §9, §14
- Tools: Python, PyTorch or Hugging Face Transformers, cocotb, Icarus or Verilator, Yosys/OpenROAD (or Vivado).

## Design

Repo layout (proposed; confirm in Stage 1):

```
rtl/            SystemVerilog or Verilog sources
tb/             cocotb testbenches
model/          Python golden model and float reference
export/         weight and activation export scripts (versioned)
synth/          synthesis scripts and constraints
results/        generated tables, plots, and logs (scripted output only)
docs/           plan, design docs, decision log
```

- Pin Python dependencies in one file (`requirements.txt` or `pyproject.toml`).
- One entry point (for example `make test`, `make export`, `make results`). A Makefile is enough; no build framework.
- Commit generated files only if they are small. Otherwise regenerate them and gitignore them.

## Deliverables

- [x] Repo skeleton with the layout above
- [x] Pinned dependencies and install steps (README)
- [x] `make test` runs cocotb with one passing smoke test (passes in WSL, Icarus 14.0, cocotb 1.9.2)
- [x] Decision log file present ([../decision-log.md](../decision-log.md))
- [x] First commit on `main`. Setup was on `feat/stage-0-setup` and merged to `main` through PR #2.

## Verification

- Fresh clone in a new directory, then install and `make test`. It must pass with no edits. **Done 2026-10-10** on a clone of `4516160`, in a new Python 3.12 venv built from `requirements.txt`. `make test` passes (1 of 1). `make export` passes and lands on the pinned revision. `make golden` reproduces the tracked log exactly. The manifest differs only in the torch build string (`2.5.1+cu124` on the fresh install, `2.5.1+cpu` in the committed manifest). The model came from the Hugging Face cache on the same account, so a new machine would also download it.

## Decisions

- See decision-log rows dated 2026-10-09 for the synthesis-flow recommendation.
- Simulator: Icarus Verilog 14.0 under WSL. Python 3.12 via uv. Logged in [decision-log](../decision-log.md).

## Risks

- Tool install on Windows (Icarus, Verilator, Yosys). Mitigation: check which simulator runs on this machine first, possibly under WSL. Record the choice in the decision log.

## Results

_Filled at exit._

## Surprises

_Filled as they happen._
