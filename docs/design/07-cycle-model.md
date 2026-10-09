# Stage 7: Cycle Model (Optional)

**Status:** Not started · **Weeks:** 9 · **Depends on:** Stage 4 (measured cycles)
**Exit criterion:** Predicted vs. measured cycles compared for both variants.

**Optional.** Drop this stage first if Weeks 5–8 slip. Record the drop in the decision log under type **gate**.

## Goal

Write a simple analytical cycle model for one run and check it against the simulated cycle counts. This ties the decode-regime argument (PRD §2) to measurements.

## Inputs

- Measured cycle counts from Stage 4
- Tile size, weight-load bandwidth, and pipeline depth from the RTL

## Design

- Model: `cycles ≈ weight_load_cycles + compute_cycles + requant_cycles + overhead`, with each term written from the RTL, not fitted.
- Weight-load term should dominate for batch-1 decode. Check that claim against the measurements.
- Report the gap between model and measurement and explain it.

## Deliverables

- [ ] Written cycle model with each term tied to an RTL parameter
- [ ] Predicted vs. measured table for both variants
- [ ] Explanation of the gap

## Verification

- The model must predict the simulated count for at least one tile size other than the one it was fitted on.

## Decisions

_Log in [decision-log](../decision-log.md)._

## Risks

- Model is too detailed to finish. Mitigation: keep the four-term model above and stop.

## Results

_Filled at exit._

## Surprises

_Filled as they happen._
