# Stage 5: Synthesis

**Status:** Not started · **Weeks:** 7 · **Depends on:** Stage 4 (both variants bit-exact)
**Exit criterion:** Area and fmax reported for both variants, from scripts, with logs linked.

## Goal

Measure area and fmax for each variant. PRD G4, FR9.

## Inputs

- Stage 4 RTL for both variants
- Synthesis target (open question, PRD §15)

## Design

### Synthesis target: recommendation

Use **Yosys + OpenROAD**. Both are open-source and scriptable, so the flow runs from a clean checkout (PRD §9). Vivado is fine if it is already installed. Record the final choice in the decision log.

- Constraints file with one target clock. The PRD allows relaxing it if timing fails; report the achieved fmax, not the target.
- Area: cell count and, where the flow reports it, post-place area. State which one.
- Run each variant with the same script and the same constraints.

### Board

No board is assumed. Simulation and synthesis only (PRD §13, low–medium risk). If bring-up is attempted, it is a separate, optional stage outside this plan.

## Deliverables

- [ ] Synthesis script that takes a variant parameter
- [ ] Clock constraint file
- [ ] Area and fmax table for both variants
- [ ] Logs for each run, linked from the table

## Verification

- Re-run one variant twice and confirm the same numbers. Record any tool nondeterminism.

## Decisions

_Log in [decision-log](../decision-log.md)._

## Risks

- Timing closure fails at target clock. Mitigation: relax the clock; report achieved fmax.

## Results

_Filled at exit._

## Surprises

_Filled as they happen._
