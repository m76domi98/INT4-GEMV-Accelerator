# Stage 2: Processing Element and Array

**Status:** Not started · **Weeks:** 2–3 · **Depends on:** Stage 1 (frozen numeric format, golden model)
**Exit criterion:** Random PE tests and real-layer tile tests pass, bit-exact against the golden model.

## Goal

Build one MAC PE, then a small tile of PEs in the chosen dataflow. Verify both bit-exact. PRD FR3, FR4, FR8.

## Inputs

- Stage 1 numeric format table and golden model
- PRD §13 (bit-exact mismatch, array size risk)

## Design

- **PE:** signed INT8 activation × signed INT4 weight, added into an accumulator of the frozen width. Interface: valid/ready on activation in, accumulate-clear, result out.
- **Array (tile):** start small, for example 4×4 PEs. Dataflow is the one baseline architecture from the PRD. Keep the tile size as a parameter.
- **Testbench:** cocotb random vectors at PE level first; then one real-layer tile slice from exported data.

### Week 3 gate

The PRD requires a decision at the end of Week 3 about array size. Decide whether the full array fits the remaining time. If not, shrink to a smaller tile and keep the same dataflow. Record it in the decision log under type **gate**.

## Deliverables

- [ ] PE RTL with parameterized widths
- [ ] PE cocotb test: random vectors, bit-exact
- [ ] Tile RTL, parameterized size
- [ ] Tile test on real-layer data, bit-exact
- [ ] Week 3 gate outcome recorded

## Verification

- Debug at PE level before the tile. The golden model is the source of truth (PRD §13).
- Include corner cases: maximum and minimum INT8 × INT4 products, accumulator at its worst-case K.

## Decisions

_Log in [decision-log](../decision-log.md)._

## Risks

- Array size exceeds available time. Mitigation: Week 3 gate.
- Bit-exact mismatch. Mitigation: PE-level tests and corner-case vectors before the tile.

## Results

_Filled at exit._

## Surprises

_Filled as they happen._
