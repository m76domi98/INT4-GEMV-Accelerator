# Stage 3: Control and Memory

**Status:** Design (decided 2026-10-10), RTL not started · **Weeks:** 4 · **Depends on:** Stage 2 (tile passes)
**Exit criterion:** A full layer runs in simulation and matches the golden model bit-exact.

## Goal

Wrap the tile in control and storage so one full layer runs per run. PRD FR5, FR6.

**Scope warning.** Stage 3 cycle counts measure compute only, with a one-cycle memory. They are not decode latency. The one-cycle memory hides the weight-bandwidth bottleneck, which is the central question of the study. Stage 7 adds read latency through the `READ_LAT` parameter, and the Stage 6 results depend on that. Nobody should read a Stage 3 cycle count as a decode time.

## Inputs

- Stage 2 tile (`rtl/pe_tile.sv`, passes random, real-layer, pause, and missing-`clr` tests)
- Stage 1 requantization spec and the golden model (`model/golden.py`, `gemv_int`)
- Stage 1 export: `q_pc`, `s_r_pc`, `m_pc` (per-channel chosen design), `x_cal_int`, `x_test_int`

## Design

**Layer shape:** 1536 output rows, K = 576 terms. With `TILE_ROWS = 4` (Week 3 gate): 384 row groups. Each group runs K terms through one tile, then requantizes its four accumulators.

**Memory (`READ_LAT`, parameter, set to 1):**
- Weight memory: one word per (row group, term). A word holds the four row weights, 4 × 4 bits = 16 bits. Loaded once per run.
- Scale memory: `M_r` per output row, 16-bit signed, loaded once per run. The export's maximum is 30,917, so 16 bits is enough.
- Activation buffer: one INT8 vector of 576 values per run.
- Output buffer: one INT8 vector of 1536 values per run. Read by the testbench after `done`.
- Reads go through a `READ_LAT`-cycle pipeline. Stage 3 only tests `READ_LAT = 1`. Stage 7 may add latency by changing the parameter, and the control must not need rewriting.

**FSM:** `IDLE → LOAD → COMPUTE → REQUANT → WRITE → DONE`.
- `LOAD`: weight, scale, and activation writes from the testbench. Counted as load cycles, not compute.
- `COMPUTE`: for each row group, K terms with `clr = 1` on term 0. The control issues `clr` itself.
- `REQUANT`: the four tile accumulators go through the requant module, one per tile row. Outputs go to the output buffer.
- `DONE`: a single-cycle `done` pulse, with the output buffer valid.

**Interface of `rtl/layer_ctrl.sv` (as built for the test).**
- Control: `clk`, `rst` (synchronous), `start` (pulse in IDLE), `load_done` (ends LOAD).
- Load writes, accepted in LOAD only: `w_we/w_addr[17:0]/w_wdata[15:0]` (word index g·K + t), `m_we/m_addr[10:0]/m_wdata[15:0]`, `x_we/x_addr[9:0]/x_wdata[7:0]`.
- Output: `out_raddr[10:0]` → `out_rdata[7:0]` (combinational read of the output buffer), `layer_done` (one cycle), `err_sticky`, `sat_count[10:0]`, `compute_cycles[31:0]`, `load_cycles[31:0]`.
- Probes for the test: `t_valid`, `t_clr`, `t_x[7:0]`, `t_w[15:0]`, the term the tile samples on the next edge.
- Reads go through a `READ_LAT`-deep pipeline after the address. The tile sees the piped values.

**Deviations from the FSM above, made while writing the test (2026-10-10):**
- No `WRITE` state. Each group's four results go to the output buffer in `REQUANT`, one row per cycle.
- `COMPUTE` issues the K terms of a group, then waits for the control's own `expect_done`, not the tile's `done`. The FSM advances on the control's expectation, so a fault that stops `done` from firing cannot hang the run. The sticky check reports it.
- Reset does not clear the memories. Every run rewrites every word, and clearing 221k words on reset is wasted simulation time. The run's correctness does not depend on the old contents.
- `sat_count` is cleared by `start` and by `rst`, not on every idle cycle. Clearing it while idle would wipe the count before the testbench reads it.

**Requantization module (`rtl/requant.sv`).** Separate from the control, so it can be tested alone.
- Interface and arithmetic match `gemv_int` exactly: `y = clamp((acc × M_r + 2^14) >>> 15, -128, 127)`.
- Inputs: `acc` (21-bit signed), `m` (16-bit signed). Output: `y` (INT8).
- Output: a saturation flag per call (`sat`), and a saturation counter (`sat_count`) that counts clipped outputs in the current run. The control clears it at the start of each run, and reset clears it too. The counter lives in the requant module, not in the output stage. Stage 6 needs this count. The spec predicted zero saturations, and Stage 1 measured 1,084 across the 118 calibration vectors.
- Product width: 21 bits × 16 bits is about 37 bits. The module uses 40 bits, so the product and the rounding cannot overflow.

**Error handling (sticky).**
- The control counts accepted terms with its own counter, independent of the tile's.
- **Timing.** The tile registers `done`, so it goes high one cycle after the Kth accepted term. The control registers its own expectation on the same edge: `expect_done <= in_valid && (count == K-1)`. Each cycle during `COMPUTE`, the check compares `done` with `expect_done`. Both signals are one cycle late, so they line up. Comparing `done` with the raw term count on the same cycle would flag every row set as an error.
- Gaps are handled by the same rule. `expect_done` is set only by accepted terms, so idle cycles keep it low, as the tile does.
- Any mismatch sets `err_sticky`.
- A missing `clr` shows up as a mismatch, because the tile does not restart its count.
- `err_sticky` stays high until `rst`. It does not clear on the next good row set. A flag that clears can be missed in a results run, and a missing `clr` silently merges two rows, which is the worst failure in this design.

**Cycle counter.** Counts compute cycles per run (`COMPUTE` + `REQUANT`), outside the datapath. Load cycles are counted separately. Both are reported, and both are labeled as one-cycle-memory numbers.

**Driver/control `clr` check.** The Stage 2 driver contract says the control must produce `clr` the same way the testbench does. The full-layer test drives the same data through a testbench-side `clr` schedule and compares it with the control's `clr` on every term.

## Deliverables

- [ ] Parameter `READ_LAT` (= 1), used by the memory interfaces
- [ ] Requantization module `rtl/requant.sv`, with saturation flag and per-run counter
- [ ] Requant unit test against `gemv_int`, on the same vectors: random accumulators, the ±2^20 extremes, and the export's M_r extremes (1,723 and 30,917 for `m_pc`)
- [ ] Control FSM and memory interfaces `rtl/layer_ctrl.sv`
- [ ] Full-layer cocotb test on real exported data, bit-exact, element by element, every row. Routine target `make test-layer` runs two vectors, one from `x_cal_int` and one from `x_test_int`. The full set of 175 vectors is a separate target, `make test-layer-full`, run once and logged, not part of routine regression. Runtime of each run is logged.
- [ ] Control `clr` compared with the testbench `clr` on every term
- [ ] Sticky error test, run against a deliberately broken copy of the control built by a Makefile target. Production RTL has no fault-injection hook. The test checks that `err_sticky` is set, stays set across a good run, and clears only on reset
- [ ] Reset test: run twice from reset, same output both times, and `err_sticky` cleared by reset
- [ ] Cycle count reported per run, labeled compute-only with one-cycle memory

## Verification

- Full-layer output compared element by element to `gemv_int`, every row, on two vectors in `make test-layer`, and on all 175 vectors in `make test-layer-full`.
- The requant unit test and the full-layer test use the same vectors, so a mismatch in either points to the same place.
- Missing-`clr` fault injection through the broken-copy target, as above.
- Two runs from reset give identical outputs and cycle counts.

## Decisions

_Logged in [decision-log](../decision-log.md) on 2026-10-10._

## Risks

- **One-cycle memory hides the bandwidth bottleneck.** This is the central risk of the study. Stage 3 cycle counts are compute only. Stage 7 adds read latency through `READ_LAT`.
- Weight-load time dominates the total cycle count. This is expected for decode, and it is a result for Stage 6, not a bug.
- Requant saturation counts can be large on real data (Stage 1 measured 1,084 across the calibration vectors). One run is one vector, so a run's count is at most 1,536. The counter is 11 bits wide to hold that, and it must not wrap.
- Full-layer simulation time: about 221k compute cycles per vector, plus about 221k load cycles if weights reload every run. The Stage 2 real-layer test ran about 6.5k cycles per second under Icarus and cocotb. At that rate one full run is roughly 70 s. That figure is an extrapolation, not a measurement. The full 175-vector set would take hours, so it is a separate target. Keep the routine test at two vectors and log the runtime of every run.

## Results

_Filled at exit._

## Surprises

_Filled as they happen._
