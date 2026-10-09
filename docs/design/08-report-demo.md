# Stage 8: Report and Demo

**Status:** Not started · **Weeks:** 10 · **Depends on:** Stages 1–6 (Stage 7 if done)
**Exit criterion:** Report and demo submitted.

## Goal

Write the 6–10 page report and record or give the demo. PRD §11 deliverables 2, 3, 5.

## Inputs

- All stage design docs and results tables
- Decision log
- Week 1 spec with predicted results

## Design

### Report outline (PRD §11, 6–10 pages)

1. Question (PRD §3) and why decode-time GEMV (PRD §2)
2. Method: model, layer, numeric format, golden model, design, variants
3. Results: area, fmax, cycles, error, from the generated table
4. Analysis: Stage 6 findings, with predicted vs. measured
5. Negative results and failed variants (PRD §9, honesty)
6. Limitations: simulation and synthesis only (if no board); scope
7. Future Work (PRD §16)

### Demo

Short, 3–5 minutes. Show: one `make` command regenerating the results table, one bit-exact test passing, and the error plot.

## Deliverables

- [ ] Report draft, then final
- [ ] Results table and figures regenerated from a clean checkout
- [ ] README: setup, tests, data regeneration (PRD §9)
- [ ] Demo recorded or scheduled
- [ ] Final CHANGELOG entry for the release

## Verification

- Clean-checkout rebuild of every table and figure, with the numbers in the report matching the generated output.
- Read the Week 1 predictions and the measured results side by side.

## Decisions

_Log in [decision-log](../decision-log.md)._

## Risks

- Report written from memory rather than from logs. Mitigation: each figure cites its script and log.

## Results

_Filled at exit._

## Surprises

_Filled as they happen._
