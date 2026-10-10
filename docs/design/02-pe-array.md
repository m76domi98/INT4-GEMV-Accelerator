# Stage 2: Processing Element and Array

**Status:** Done (2026-10-09) · **Weeks:** 2–3 · **Depends on:** Stage 1 (frozen numeric format, golden model)
**Exit criterion:** Random PE tests and real-layer tile tests pass, bit-exact against the golden model.

## Goal

Build one MAC PE, then a small tile of PEs in the chosen dataflow. Verify both bit-exact. PRD FR3, FR4, FR8.

## Inputs

- Stage 1 numeric format table and golden model
- PRD §13 (bit-exact mismatch, array size risk)

## Decisions (frozen before RTL)

| Item | Decision | Why |
| --- | --- | --- |
| Baseline dataflow | **Output-stationary** | Neither dataflow saves weight reads at batch 1, since each weight is read once per token. The difference is where the 21-bit partial sums live. Output-stationary keeps them local to each PE, so they never move between PEs. Weight-stationary moves them every cycle. |
| Tile output | **Raw 21-bit accumulator per row**. Requantization (FR6) is not in the tile | Keeps the Stage 2 check a pure integer comparison against `acc`. Requant comes in Stage 3 with the control block. |
| Tile size | **4 rows** (`TILE_ROWS = 4`), a parameter | Small enough to debug by hand. Shrink to 2 at the Week 3 gate if needed. |
| Valid/ready | **Valid only.** No ready | Stage 2 has no backpressure. The stream is driven by the testbench. Ready comes back in Stage 3 if the control FSM needs it. |
| Done signal | **Tile raises `done` for one cycle** after the Kth valid term | The tile knows K from a parameter and counts terms. Gives Stage 3 a defined point to sample `acc`. The PE has no notion of done. |
| `clr` framing | **Driver asserts `clr` on term 0 of each row.** PE does not count terms | Keeps the PE a plain accumulator. Cost: the counter lives in the driver, so Stage 3 control must produce `clr` the same way (see Deliverables). |
| Corner-case tests | **One cocotb test per case**, named by case (e.g. `int8_min_x_int4_max`) | One command runs them all, and a failure names the case that broke. |

## Design

**Widths (derived, frozen):**
- Activation: signed INT8, `[-127, 127]`.
- Weight: signed INT4, `[-8, 7]`.
- Product: `[-1016, 1016]`, so **11-bit signed** (`PROD_W = 11`).
- Accumulator: **21-bit signed** (`ACC_W = 21`). Worst case `576 × 1016 = 585,216` fits in ±1,048,575.

**PE:** one MAC. Each cycle with `in_valid`, `acc <= acc + x × w`. A `clr` input loads the accumulator with the first product, so the next output row starts clean. `acc` is held until the next `clr`.

- Parameters: `PROD_W = 11`, `ACC_W = 21`.
- Ports: `clk`, `in_valid`, `clr`, `x` (signed 8-bit, broadcast), `w` (signed 4-bit, this row's own), `acc` (signed `ACC_W`, output).

**Tile (`pe_tile`):** parameters `TILE_ROWS`, `K`, plus `PROD_W` and `ACC_W` passed to each PE. Ports: `clk`, `in_valid`, `clr`, `x`, `w` (flat, row `r` at bits `[4r+3:4r]`), `acc` (flat, row `r` at bits `[ACC_W·r+ACC_W-1 : ACC_W·r]`), `done` (high in the cycle after the Kth valid term, when `acc` is final). The tile counts terms from `clr`, so the driver's `clr` on term 0 is the only framing it needs.

**Driver contract:** every row set must start with `clr = 1` on term 0. The tile does not check this. If term 0 has `clr = 0`, the tile adds into the previous row set's sum and `done` does not fire at the end of that row set. `missing_clr_accumulates_and_drops_done` in `tb/test_tile.py` pins this behavior. Stage 3 control must produce `clr` correctly and add a sticky error flag for a missing `clr`.

**Tile:** `TILE_ROWS` PEs, one per output row `r0 … r0+TILE_ROWS-1`. Each cycle `i` (0 to K−1):
- The activation `x_i` is **broadcast** to every PE in the tile.
- PE `r` takes its own weight `q[r0+r][i]`. These are different weights for each row, read from memory.
- After the Kth valid term the tile raises `done` for one cycle. The accumulators are final and stable until the next `clr`. Partial sums never leave a PE.

For the real layer (`K = 576`, `N = 1536`): `1536 / 4 = 384` tiles, 576 cycles each. That is about 221k cycles per token before control overhead. The cycle model (Stage 7) will check this number.

**Testbench (cocotb, bit-exact):**
1. **PE random:** random `(x, w)` pairs, accumulate over K terms, compare `acc` to a Python integer reference.
2. **PE corner cases:** every combination of `x ∈ {-127, -1, 0, 1, 127}` and `w ∈ [-8, 7]`, each as its own cocotb test named by case (e.g. `int8_min_x_int4_max`). Plus the worst-case accumulator: 576 terms of `x = -127, w = -8` (`+585,216`), and `x = 127, w = -8` (`-585,216`). `x = -128` is out of range per `golden.py` (`x_int` in `[-127, 127]`), so it is not tested.
3. **Tile random:** random 4 × 576 weights and activations.
4. **Tile real layer:** rows 0–3 of `q_pc` from `export/out/layer15_up_proj.npz`, run on the calibration activation vectors (`x_cal_int`). Expected `acc` comes from the golden model.

**Golden model change needed:** `model/golden.py` returns requantized `y` only. Add a helper that returns the raw per-row `acc` for one vector, so the tile test can compare accumulators. This is an addition, not a change to the existing function.

**Makefile:** `TOPLEVEL` and `VERILOG_SOURCES` are set once for `smoke_top`. Each Stage 2 module needs its own test target. Plan: one target per module (`test-pe`, `test-tile`).

### Week 3 gate

The PRD requires a decision at the end of Week 3 about array size. Decide whether the full array fits the remaining time. If not, shrink to a smaller tile and keep the same dataflow. Record it in the decision log under type **gate**.

## Deliverables

- [x] Golden helper returning raw per-row `acc` (for the tile test)
- [x] PE RTL with parameterized widths (`PROD_W`, `ACC_W`)
- [x] PE cocotb test: random vectors and corner cases, bit-exact (84 of 84 under WSL, Icarus)
- [x] Tile RTL, parameterized `TILE_ROWS` and `K`
- [x] Tile test on random data, bit-exact (20 runs, K = 576, TILE_ROWS = 4)
- [x] Tile test on real-layer data, bit-exact (rows 0–3 of `q_pc`, all 118 calibration vectors)
- [ ] Week 3 gate outcome recorded
- [ ] Stage 3 (not Stage 2): tile-level check that the control's `clr` matches the testbench's `clr` on every row, so a mismatch fails loudly

## Verification

- Debug at PE level before the tile. The golden model is the source of truth (PRD §13).
- Corner cases: maximum and minimum INT8 × INT4 products, accumulator at its worst-case K.

## Decisions

_Logged in [decision-log](../decision-log.md)._

## Risks

- Array size exceeds available time. Mitigation: Week 3 gate.
- Bit-exact mismatch. Mitigation: PE-level tests and corner-case vectors before the tile.
- Output-stationary moves the weight bandwidth problem into the memory side (one weight per row per cycle). Mitigation: the Stage 3 memory design, and the Stage 6 measurements.

## Results

Exit criterion met: random PE tests and real-layer tile tests pass, bit-exact against the golden model. Run under WSL, Icarus 14.0, cocotb 1.9.2.

- **PE** (`make test-pe`): 84 of 84 pass. That covers 80 corner cases (the 5 × 16 grid of `x` and `w`), the worst-case accumulator at ±585,216 over K = 576, 200 seeded random dot products, and the idle-hold check.
- **Tile** (`make test-tile`, TILE_ROWS = 4, K = 576): 3 of 3 pass.
  - Random: 20 runs, bit-exact on every row.
  - Done and hold: `done` is high for exactly one cycle after the Kth term, and `acc` holds after it.
  - Real layer: rows 0–3 of `q_pc` on all 118 calibration vectors from the export, bit-exact.
- **Smoke** (`make test`): still passes with the new modules in `rtl/`.
- **Timing:** one term per cycle, no pipeline stages. A K-term dot product takes K cycles, and `done` lands one cycle after the last term. The per-token cycle count for the full layer is Stage 7's job.

Test-first record: the red runs failed for three reasons: the RTL did not exist yet, a cocotb decorator error, and then a timescale error (see Surprises). The green run came after the RTL was written.

## Surprises

- **Command-line `COMPILE_ARGS` drops the timescale.** Passing `COMPILE_ARGS=...` on the `make` command line replaces cocotb's own compile args, including the `-f cmds.f` that sets the timescale. The build then failed with `Unable to accurately represent 10(ns)`. Fix: pass the tile parameters as an environment variable. Makefile `+=` appends to it, so cocotb's args survive.
- **cocotb 1.9.2 has no `name=` on `@cocotb.test`.** The first version of the corner-test factory used it and failed at import. Setting `__name__` alone also didn't rename the test in the report, because cocotb reads `__qualname__`. The factory now sets both before wrapping.
- **Stale build directory.** After a failed tile run, the next build failed in the same way. A clean rebuild (removing `sim_build/pe_tile`) passed. I did not pin down what was stale.
- **`make test-tile` does not work under Verilator right now.** The `-P` flags are Icarus syntax, and Verilator takes parameters with `-G`. The tile target is Icarus only until someone adds the Verilator branch and runs it.
