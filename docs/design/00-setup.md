# Stage 0: Setup

**Status:** Not started · **Weeks:** Setup (before Week 1) · **Depends on:** PRD Draft v1
**Exit criterion:** A clean checkout runs the test command and the export command, both with no manual steps.

## Goal

Make the repo reproducible before any design work starts. PRD §9 requires one command to rerun simulation and regenerate the results table from a clean checkout.

## Inputs

- [PRD](../../PRD%20Decode-Time%20INT4%20GEMV%20Accelerator%20Study.md) §9, §14
- Tools: Python, PyTorch or Hugging Face Transformers, cocotb, Icarus or Verilator, Yosys/OpenROAD (or Vivado)

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

- [ ] Repo skeleton with the layout above
- [ ] Pinned dependencies and install steps (README)
- [ ] `make test` runs cocotb with one passing smoke test
- [ ] Decision log file present ([../decision-log.md](../decision-log.md))
- [ ] First commit on `main`. The repo has no commits yet, so this is the first one.

## Verification

- Fresh clone in a new directory, then install and `make test`. It must pass with no edits.

## Decisions

- See decision-log rows dated 2026-10-09 for the synthesis-flow recommendation.

## Risks

- Tool install on Windows (Icarus, Verilator, Yosys). Mitigation: check which simulator runs on this machine first, possibly under WSL. Record the choice in the decision log.

## Results

_Filled at exit._

## Surprises

_Filled as they happen._
