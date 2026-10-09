# Stage 3: Control and Memory

**Status:** Not started · **Weeks:** 4 · **Depends on:** Stage 2 (tile passes)
**Exit criterion:** A full layer runs in simulation and matches the golden model bit-exact.

## Goal

Wrap the tile in control and storage so one full layer runs per run. PRD FR5, FR6.

## Inputs

- Stage 2 tile
- Stage 1 requantization spec

## Design

- **Memory:** BRAM (or register file in simulation) for weights, loaded once per run. Activation and output buffers sized for one vector.
- **FSM:** load weights → stream activations → tile compute → requantize → write outputs → done. Status signal for the testbench.
- **Requantization (FR6):** implements the Stage 1 scheme exactly. Per-channel scales, if chosen, are read from a small scale memory indexed by output row.
- **Cycle counter:** counts cycles per run for FR9. Keep it outside the datapath.

## Deliverables

- [ ] Control FSM and memory interface
- [ ] Requantization block, unit-tested against the golden model
- [ ] Full-layer cocotb test on real exported data, bit-exact
- [ ] Cycle count reported per run

## Verification

- Full-layer output compared element by element to the golden model.
- Run twice from reset to check that state does not leak between runs.

## Decisions

_Log in [decision-log](../decision-log.md)._

## Risks

- Weight-load time dominates the cycle count. This is expected for decode, and it is a result for Stage 6, not a bug.

## Results

_Filled at exit._

## Surprises

_Filled as they happen._
