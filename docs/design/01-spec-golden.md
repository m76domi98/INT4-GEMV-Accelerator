# Stage 1: Question, Model, Layer, Spec, Golden Model

**Status:** Not started · **Weeks:** 1 · **Depends on:** Stage 0
**Exit criterion:** Golden model within the stated error bound of the float layer; spec written and dated before any RTL.

## Goal

Freeze the question, the model, the layer, and the number formats. Write the golden model. Write predicted results down before measuring anything. PRD §12 and §15.

## Inputs

- PRD §3 (research question), §6 (scope), §8 FR1–FR2, §15 (open questions)

## Design

### Open questions to close this week

- [ ] **Model.** Pick one small decoder-only model with a permissive license (Apache-2.0 or MIT). Record name, parameter count, and license. Verify the license on the model card; do not rely on this doc.
- [ ] **Layer.** Recommend the FFN up-projection. It is the largest matrix in most small decoders, so bandwidth dominates more clearly than in Q.
- [ ] **Design decision.** See the recommendation below.
- [ ] **Synthesis target.** See [05-synthesis](05-synthesis.md).

### Recommended design decision: per-channel vs. per-tensor requantization

Dataflow is a weak choice for this study. In GEMV with batch 1, every weight is used exactly once per token, so output-stationary and weight-stationary differ mostly in where partial sums sit, not in reuse. Accumulator width changes overflow behavior but gives little to analyze.

Per-channel vs. per-tensor requantization is a better fit:

- It directly serves G3 (error by row and by outlier channel). Per-tensor scales hide the rows that matter.
- The hardware cost is small: one scale per output row, stored in a small memory, versus one global scale.
- Both variants share the same datapath, so the area and fmax comparison in Stage 5 isolates the scale path.

If the team prefers dataflow, the study still works, but the analysis in Stage 6 gets thinner. Record the final choice here and in the decision log.

### Numeric format (to fill and freeze)

| Item | Value | Notes |
| --- | --- | --- |
| Activation | signed INT8 | Per-tensor scale, chosen from calibration data |
| Weight | signed INT4 | Symmetric; state group size if grouped |
| Accumulator | TBD | Check the worst case: K × 127 × 7 bits plus margin |
| Requantization | TBD | Scale, rounding mode, saturation range |
| Output | INT8 (or wider) | State the format |
| Error bound | TBD | Golden vs. float; set before measuring |

### Golden model

- Pure Python integer arithmetic. No NumPy floats inside the datapath.
- Input: exported weights and activation vectors (FR2). Output: integer vector plus the float reference.
- Report: max abs error, RMSE, and per-row error. These feed G3 later.

## Deliverables

- [ ] Model and layer recorded in this doc
- [ ] Numeric format table frozen
- [ ] Versioned export script (FR2) with a shape check and a known-output check
- [ ] Golden model passes the error bound on the exported layer
- [ ] **Spec file with predicted results**, dated, and not edited after RTL starts (Working Agreement)

## Verification

- Shape check: exported matrix shape matches the model config.
- Known-output check: run one hand-computed vector through the export path (PRD §13, transposed-weight risk).
- Bound check: golden vs. float on every exported activation vector.

## Decisions

_Log in [decision-log](../decision-log.md)._

## Risks

- Transposed or wrong-layout weights (PRD §13). Mitigation: the known-output check above.
- Error bound too loose to mean anything. Mitigation: set it from the INT8 and INT4 rounding budget before measuring.

## Results

_Filled at exit._

## Surprises

_Filled as they happen._
