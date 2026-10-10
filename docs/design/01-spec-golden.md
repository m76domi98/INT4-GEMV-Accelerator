# Stage 1: Question, Model, Layer, Spec, Golden Model

**Status:** Done (2026-10-09) · **Weeks:** 1 · **Depends on:** Stage 0
**Exit criterion:** Golden model within the stated error bound of the float layer; spec written and dated before any RTL.
**Spec date:** 2026-10-09. Sections marked *frozen* must not change after RTL starts. Changes go in a new dated section.

## Goal

Freeze the question, the model, the layer, and the number formats. Write the golden model. Write predicted results down before measuring anything. PRD §12 and §15.

## Inputs

- PRD §3 (research question), §6 (scope), §8 FR1–FR2, §15 (open questions)

## Decisions (frozen)

| Item | Decision | Source |
| --- | --- | --- |
| Model | **SmolLM2-135M** (HuggingFaceTB), Apache-2.0 | License read from the model card (`apache-2.0`) on 2026-10-09. Re-check before freezing. |
| Architecture | Llama-style, SiLU gated MLP. `hidden_size` 576, `intermediate_size` 1536, 30 layers | `config.json` on 2026-10-09 |
| Layer | `model.layers.15.mlp.up_proj`, weight shape **[1536, 576]** (out × in). Input K = 576, output N = 1536 | Middle layer of 30. Gate and down projections are out of scope. |
| Design decision | **Per-channel requantization** (one scale per output row) vs. per-tensor as the comparison | PRD §3 candidates. Dataflow and accumulator width are not the variable under study. |
| Synthesis | **Yosys + OpenROAD** | Free and scriptable. Vivado is a fallback only if it is already installed. |
| Board | None. Simulation and synthesis only | PRD §13 |

**Why this layer:** the up-projection has the most weight bytes per token among the MLP matrices in this model, so it is the clearest test of the memory-bound regime (PRD §2).

**Why a smaller model:** the export, golden model, and cocotb runs must iterate quickly on a laptop. SmolLM2-135M's 1536×576 matrix is about 0.9M weights, which is small enough for full-layer simulation.

**Why per-channel requantization:** it is the standard choice in practice. Per-tensor scales are set by the global maximum, which leaves rows with small weights with few quantization levels. That gives an error pattern across rows to analyze (G3). The cost is one scale per row, 1536 entries.

## Numeric format (frozen)

| Item | Value | Notes |
| --- | --- | --- |
| Activation | signed INT8, symmetric, **per-tensor** | `s_x = max|x_cal| / 127`. `x_int = clamp(round(x / s_x), -127, 127)`. |
| Weight | signed INT4, symmetric, **per output row** | `s_r = max_i |w_ri| / 7`. `q = clamp(round(w / s_r), -8, 7)`. Full range [-8, 7] is used in the datapath. |
| Product | at most 127 × 8 = **1016** in magnitude | Bounds the accumulator |
| Accumulator | **signed 21-bit**. K = 576 gives worst case 1016 × 576 = **585,216**. 21-bit range is ±1,048,575 | Worst-case width, fixed for the spec. The real-weight check is in Predictions. |
| Requantization | `acc_int` to INT8 output using fixed-point multiplier `M_r` and shift 15 | `M_r = round(s_x · s_r / s_out_r · 2^15)`. Golden: `y = clamp(((acc · M_r) + 2^14) >> 15, -128, 127)`. |
| Output scale | `s_out_r = max_cal |y_float_r| / 127`, per row | Calibrated on the same calibration set as `s_x`. |
| Output | signed INT8 | Dequantized output is `y_int · s_out_r`. |

Notes:
- Integer ops only inside the golden datapath. The float reference lives outside it.
- `M_r` is 16 bits or less in practice. The exact multiplier width is a Stage 3 hardware detail. The golden model defines the arithmetic now, so RTL must match it bit for bit.
- Saturation should not trigger on calibrated data. Count saturations in the golden run and report the count.

## Error bound (predicted, frozen)

The reference is the float matmul `y_r = Σ_i w_ri · x_i` with float weights and float input. Let `ŵ` and `x̂` be the dequantized values.

Three terms bound `|ŷ_r − y_r|`:

1. **Weight rounding:** `E_w,r = (s_r / 2) · Σ_i |x̂_i|`. Each weight error is at most `s_r / 2`.
2. **Activation rounding:** `E_x,r = (s_x / 2) · Σ_i |ŵ_ri|`.
3. **Requantization:** `E_rq,r = s_out_r / 2`, plus any saturation (expected 0).

Total: `E_r = E_w,r + E_x,r + E_rq,r`.

Worst-case closed form, using `|x̂_i| ≤ 127 · s_x` and `|ŵ| ≤ 8 · s_r`:
`E_r ≤ K · 127 · s_x · s_r / 2 + K · 8 · s_r · s_x / 2 + s_out_r / 2`.

**Acceptance:** golden output vs. float reference, per row, is within `E_r` on every calibration and test vector. Report the numeric values of `E_r` once the export runs. The formula is fixed now.

Random-sign sums grow like √K, not K, so measured error should sit well below this worst case. The RMS form is `E_w,rms = s_r · √(K/12) · rms(x̂)` and is the more realistic comparison.

## Predictions (Week 1, frozen before measuring)

- **P1.** Per-channel max abs error is less than or equal to per-tensor max abs error on the same layer. The gap is largest on rows with small `max|w|`.
- **P2.** Measured max error is below the worst-case `E_r` on every vector. It sits closer to the RMS form than to the worst case.
- **P3.** The real-weight accumulator fits in **18 bits** signed (|acc| < 131,072) on the calibration inputs, because sums grow like √K. The spec still uses 21 bits.
- **P4.** Predicted results are checked in Stage 6. Any wrong prediction goes in the surprise log with an explanation.

## Golden model

- Pure Python integer arithmetic. No NumPy floats inside the datapath.
- Input: exported weights, `s_x`, `s_r`, `M_r`, and activation vectors (FR2). Output: integer vector, plus the float reference for comparison.
- Report: max abs error, RMSE, per-row error, saturation count, and the measured max `|acc|` against 2^20. P3 is checked here.

## Deliverables

- [x] Model and layer recorded (see Decisions)
- [x] Numeric format table frozen
- [x] Error bound formula frozen
- [x] Predictions written
- [x] Versioned export script (FR2) with a shape check (expect [1536, 576]) and a known-output check
- [x] Golden model passes the error bound on the exported layer
- [x] Spec numeric values filled in (E_r, measured |acc|, saturation count)

## Verification

- Shape check: exported matrix shape is [1536, 576], which matches `config.json`.
- Known-output check: run one hand-computed vector through the export path (PRD §13, transposed-weight risk).
- Bound check: golden vs. float on every exported activation vector.

## Decisions

_Logged in [decision-log](../decision-log.md)._

## Risks

- Transposed or wrong-layout weights (PRD §13). Mitigation: the known-output check above.
- Error bound too loose to mean anything. Mitigation: the formula is fixed above and derived from the rounding budget.
- Layer 15 is unrepresentative. Mitigation: it is fixed now. Do not switch layers. Note the choice in the report's limitations.

## Results

Source: `make golden` on 2026-10-09, log in `results/stage1_golden.log`. Model revision `93efa2f0`, s_x 0.0180745. Calibration: 118 vectors. Test: 57 vectors. Each vector has 1536 rows.

| Metric | Per-channel (chosen) cal | Per-channel test | Per-tensor cal | Per-tensor test |
| --- | --- | --- | --- | --- |
| Max abs error | 0.811629 | 1.37576 | 1.7933 | 1.93254 |
| RMSE | 0.0972273 | 0.104291 | 0.351412 | 0.357824 |
| E_r min / median / max | 0.518948 / 3.17361 / 14.2691 | 0.517954 / 3.20019 / 13.9732 | 0.633072 / 11.7367 / 15.2173 | 0.625285 / 11.8769 / 14.9214 |
| E_r violations (frozen bound) | 0 (min margin 0.509446) | 0 (min margin 0.510472) | 0 | 0 |
| Violations with M term | 0 (M-term max 0.000977) | 0 (M-term max 0.000905) | 0 | 0 |
| Max \|acc\| (budget 2^20) | 2518 (0.002) | 2220 (0.002) | 745 (0.001) | 788 (0.001) |
| Requant saturations | 1084 | 1266 | 2 | 1 |
| Activation clips | 0 | 0 | 0 | 0 |

**Predictions checked (P1–P3 are checked here; P4 is Stage 6):**
- **P1: PASS.** Per-channel max error 1.37576 vs. per-tensor 1.93254 on the test set. Over all vectors, per-channel max is 1.37576 and per-tensor is 1.93254. Correlation of the per-row gap with max|w_r| is −0.321 (predicted negative).
- **P2: PASS.** Every vector's max error is below its worst-case E_r. Mean distance to the RMS form is 0.124, against 10.38 for the worst case, so the measured error is much closer to the RMS form.
- **P3: PASS.** Max |acc| on calibration is 2518, below 2^17 = 131,072. This is well under the 18-bit prediction, and the spec keeps the 21-bit width.

**Bound result:** the frozen E_r holds on every vector for both variants, including the vectors with saturations. The M_r term is tiny in practice (under 0.001 in output units), so it does not change the result.

## Surprises

- **Saturations on calibration data (2026-10-09).** The Numeric format notes predicted saturation would not trigger on calibrated data. Per-channel saturates 1084 times on calibration and 1266 on test. Per-tensor saturates 2 and 1 times. Probe on the exported arrays: the float output never exceeds 127 LSB on calibration, by construction. The golden output, computed from the quantized activations, overshoots by up to 50 LSB on 447 of 1536 rows. The M_r rounding moves the output by at most 0.52 LSB, so it is not the cause. The cause is activation quantization error. Per-channel sets each `s_out` to its own row's max, so any overshoot clips. Per-tensor has a larger `s_out` on most rows, so it has headroom. The clipped error is still inside the frozen E_r, since E_r has 0 violations. The frozen expectation was wrong and is kept as written. This is logged in the decision log.

## Amendment (2026-10-10): isolated requantization comparison

**Why.** The 2026-10-09 P1 comparison changed two things at once. `quantize_weights` and `requant_params` both took the same `per_tensor` flag, so the per-tensor variant had per-tensor INT4 weights and per-tensor output scales. The P1 result (1.376 vs. 1.933) compared two whole schemes. It did not test requantization. This amendment holds the weights fixed and changes only the output scale. The frozen Results and Predictions above are kept as written. This section replaces them for P1.

**What changed.** The export adds `s_out_iso` and `m_iso`: per-tensor output scale, computed from the per-channel weights (`q_pc`, `s_r_pc`). The chosen design is unchanged, and its numbers match the 2026-10-09 log exactly. The old per-tensor weights are kept as `q_pt` and labeled joint and exploratory. `make golden` now reports three variants. The log is in `results/stage1_golden.log`.

**Isolated results** (same per-channel weights; output scale is the only difference):

| Metric | Per-channel output (chosen) cal | test | Per-tensor output, same weights cal | test |
| --- | --- | --- | --- | --- |
| Max abs error | 0.811629 | 1.37576 | 0.800331 | 0.763927 |
| RMSE | 0.0972273 | 0.104291 | 0.0983944 | 0.0998993 |
| Requant saturations | 1084 | 1266 | 1 | 0 |
| E_r violations | 0 | 0 | 0 | 0 |
| Max \|acc\| | 2518 | 2220 | 2518 | 2220 |

The joint scheme, kept for the record, is unchanged from 2026-10-09: max error 1.7933 (cal) and 1.93254 (test), with 2 and 1 saturations.

**Predictions on the isolated comparison.**
- **P1: FAIL.** The prediction was that per-channel max error is at most per-tensor max error on the same layer. With weights held fixed, per-channel output max error is 1.37576 and per-tensor is 0.800331. Per-channel is higher on both splits, and the gap is small on calibration (0.812 vs. 0.800). The correlation of the per-row gap with max|w_r| is −0.001, against a predicted −0.321 in the joint run. The gap-vs-|w| part of the prediction is not supported.
- **RMSE is mixed.** Per-channel is slightly better on calibration (0.0972 vs. 0.0984), and per-tensor is better on test (0.0999 vs. 0.1043). The two schemes are within about 5% of each other, and which one wins depends on the split.
- **P2: PASS**, and **P3: PASS**, unchanged. Both use the chosen design, whose numbers did not change.

**Cause, partly isolated.** On the test split, 87% of the 100 largest per-channel errors are on outputs that hit the INT8 limit. On calibration, none of the top 100 are saturated. So clipping explains the test-split max error, and it does not explain the calibration gap. The calibration gap is unexplained. Separating the weight and activation contributions to it is Stage 6 error analysis.

**Consequence.** The headroom result is clean: per-tensor output scale removes almost all requant saturations (1 and 0, against 1084 and 1266), because it leaves room above the largest output. On max abs error, the per-channel output scale does not beat per-tensor here. The Stage 4 comparison should report both numbers, and it should not claim per-channel is better on max error.

**Diagnostics (2026-10-10, same export, no change to the chosen design or the frozen P1):**
- **Calibration gap is within noise.** A bootstrap over the 118 calibration vectors (5000 resamples) gives a 95% interval of −0.025 to +0.011 for the difference in max error (per-channel minus isolated per-tensor). The per-channel max is higher in 69% of resamples. The 0.812 vs. 0.800 gap is not distinguishable from sampling variation.
- **Headroom on the test split.** A per-channel margin above the calibration max lowers test max error (1.376 at 0% margin, 1.120 at 20%) and removes most clipping. It does not bring per-channel below per-tensor (0.764). The margin does not change calibration max error. So the test-split gap is partly clipping, and the calibration gap is not clipping.
- **Secondary metric is not pre-registered.** The RMSE and saturation numbers were already in the table above when this section was written. A metric chosen now is post hoc on cal and test. A clean test of a secondary prediction needs vectors that have not been measured yet, for example a new prompt set exported with the same script.
