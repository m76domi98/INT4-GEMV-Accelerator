# Project Plan: Decode-Time INT4 GEMV Accelerator Study

Source of truth for scope and requirements: [PRD](../PRD%20Decode-Time%20INT4%20GEMV%20Accelerator%20Study.md) (Draft v1, 2026-10-09).
This file turns the PRD milestones into stages. Each stage has a design doc in [docs/design/](design/) and an entry in [CHANGELOG.md](../CHANGELOG.md) when it exits.

## Stages

| Stage | Weeks | Milestone (PRD §12) | Exit criterion | Design doc | Status |
| --- | --- | --- | --- | --- | --- |
| 0 | Setup | Repo, tooling, logs | Clean checkout builds and runs the test command | [00-setup](design/00-setup.md) | In progress (fresh-clone check pending) |
| 1 | 1 | Question, model, layer, spec | Golden model within error bound; spec written before RTL | [01-spec-golden](design/01-spec-golden.md) | Done (2026-10-09) |
| 2 | 2–3 | PE and array | Random and real-layer tests pass on a small tile | [02-pe-array](design/02-pe-array.md) | Not started |
| 3 | 4 | Control and memory | Full layer runs in simulation, matches golden model | [03-control-memory](design/03-control-memory.md) | Not started |
| 4 | 5–6 | Variants implemented and measured | Results table for both variants | [04-variants](design/04-variants.md) | Not started |
| 5 | 7 | Synthesis | Area and fmax for both variants | [05-synthesis](design/05-synthesis.md) | Not started |
| 6 | 8 | Error analysis | Plots and explanations complete | [06-error-analysis](design/06-error-analysis.md) | Not started |
| 7 | 9 | Cycle model (optional) | Predicted vs. measured cycles | [07-cycle-model](design/07-cycle-model.md) | Not started |
| 8 | 10 | Report and demo | Submitted | [08-report-demo](design/08-report-demo.md) | Not started |

## Gates

Two gates can change the plan. Decide them on the date, not later.

- **Week 3 gate (PRD §13):** if the array does not fit the time budget, shrink to a smaller tile and keep the same dataflow. Record the call in the decision log.
- **Week 6 gate (PRD §13):** if the second variant is not finished, report the first variant fully and describe the second as planned work.

## Working Agreements

- **Spec before RTL.** The Week 1 spec, including predicted results, is dated and not edited after RTL starts. Changes go in a new dated section.
- **Design doc before code.** Each stage doc is written or updated before its first RTL or script change.
- **Log decisions and surprises** in [docs/decision-log.md](decision-log.md) the same day they happen. Negative results go in too.
- **Scripts make every number.** Results tables and plots come from scripts; each links to a log file (PRD §9).
- **Changelog on stage exit.** Add an entry under `[Unreleased]` when a stage's exit criterion is met.
- **Scope freeze.** Anything outside the PRD's Non-Goals goes to Future Work, not into a stage.

## Open Questions (from PRD §15)

These are due by the end of Week 1 unless noted. Each one is tracked in [01-spec-golden](design/01-spec-golden.md).

- [x] Which model and layer? SmolLM2-135M, `layers.15.mlp.up_proj` (see [01-spec-golden](design/01-spec-golden.md))
- [x] Which design decision? Per-channel vs. per-tensor requantization
- [x] Which synthesis target and board, if any? Yosys + OpenROAD, no board. ([05-synthesis](design/05-synthesis.md))
- [ ] Exact start and end dates, and any other commitments that overlap? (Not strict; schedule stays week-based until this is known)
