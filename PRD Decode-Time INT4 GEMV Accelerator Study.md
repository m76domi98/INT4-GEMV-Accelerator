# PRD: Decode-Time INT4 GEMV Accelerator Study

**Owner:** Michelle · **Status:** Draft v1 · **Term:** About 10 weeks · **Last updated:** 2026-10-09

## 1. Summary

This project builds a small RTL accelerator for one quantized linear layer from a small open LLM, running single-token decode (a matrix-vector product). It measures how one design choice affects hardware cost, numerical accuracy, and cycle count. The contribution is the measurement and analysis, not the array architecture, which is standard.

## 2. Problem

Autoregressive decode computes one token at a time. Each step is a GEMV, not a GEMM, so arithmetic intensity is low and performance is usually limited by weight bandwidth, not MAC count. Most student accelerator projects benchmark matrix multiplication at batch sizes where compute dominates. This study asks how hardware choices behave in the memory-bound decode regime, using real quantized weights.

## 3. Research Question

> For one real quantized decode-time linear layer, how does \[chosen design decision\] change area, fmax, cycle count, and output error relative to a software reference?

The decision is fixed in Week 1. Candidates: output-stationary vs. weight-stationary dataflow; accumulator width; per-channel vs. per-tensor requantization scales.

## 4. Goals

- **G1.** Build an RTL implementation of one quantized linear layer that is bit-exact against a Python golden model.
- **G2.** Compare two variants of the chosen design decision on the same layer with measured results.
- **G3.** Explain where quantization error concentrates, by row, magnitude, and outlier channel.
- **G4.** Report synthesis area and fmax for each variant.

## 5. Non-Goals

- A full LLM running on hardware, or any end-to-end token generation.
- Competitive throughput against commercial accelerators.
- Softmax or attention hardware (see Future Work).
- Training or fine-tuning any model.
- Optimizing beyond the chosen comparison.

## 6. Scope

- **Model:** one small open decoder-only model, chosen in Week 1 (record name, size, license).
- **Layer:** one linear projection (for example, attention Q or FFN up-projection), fixed in Week 1.
- **Regime:** single-token decode, one input vector and one output vector.
- **Precision:** INT8 activations, INT4 weights, wider accumulator, defined requantization.
- **Dataflow:** one baseline architecture plus the chosen variant comparison.
- **Target:** simulation and synthesis required (Vivado or Yosys/OpenROAD); board bring-up optional.

## 7. Users and Audience

- **Primary:** Michelle, building a self-directed study and portfolio artifact.
- **Secondary:** reviewers and interviewers in hardware and ML systems roles.

## 8. Functional Requirements

- **FR1. Golden model:** Python model implements exact integer arithmetic (bit widths, accumulation, requantization) and reproduces the float layer within a stated error bound.
- **FR2. Data export:** weights and sample activation vectors are exported by a versioned, reproducible script.
- **FR3. Processing element:** MAC PE accepts signed INT8 activations and INT4 weights, with an accumulator of the specified width.
- **FR4. Array:** an array (or tile) of PEs implements the chosen dataflow; size set by the Week 3 gate.
- **FR5. Control:** FSM loads weights into BRAM, streams activations, and writes outputs for one full layer per run.
- **FR6. Requantization:** converts accumulator outputs to the output format using the defined scheme.
- **FR7. Variant support:** both variants are selectable by parameter or separate module and run on the same testbench and data.
- **FR8. Testbench:** cocotb tests for PE-level random vectors and layer-level real data, compared bit-exact to the golden model.
- **FR9. Measurement:** harness reports cycle count, output error vs. reference (max abs, RMSE, per-row distribution), and synthesis area and fmax per variant.

## 9. Non-Functional Requirements

- **Reproducibility:** one command reruns simulation and regenerates the results table from a clean checkout.
- **Traceability:** every number in the report links to a script and a log file.
- **Honesty of results:** negative results and failed variants are reported, not removed.
- **Documentation:** README covers setup, tests, and data regeneration.

## 10. Success Metrics

| Metric | Target |
| --- | --- |
| Layer output matches golden model | Bit-exact on all test vectors |
| Golden model vs. float reference | Error within the bound stated in the Week 1 spec |
| Variant comparison | Results table with both variants on the same layer |
| Synthesis | Area and fmax reported for both variants |
| Error analysis | Plots and written breakdown, including at least one explained surprise |
| Predictions | Week 1 expected results compared with measured results |

## 11. Deliverables

1. Git repository with RTL, testbench, golden model, export scripts, and synthesis scripts
2. Written report (6–10 pages): question, method, results, analysis
3. Results table and figures, generated by script
4. Week 1 spec with predicted results, dated and kept unchanged
5. Short demo (recorded or live)

## 12. Milestones

| Week | Milestone | Exit criterion |
| --- | --- | --- |
| 1 | Question, model, layer, spec | Golden model within error bound; spec written before RTL |
| 2–3 | PE and array | Random and real-layer tests pass on a small tile |
| 4 | Control and memory | Full layer runs in simulation, matches golden model |
| 5–6 | Variants implemented and measured | Results table for both variants |
| 7 | Synthesis | Area and fmax for both variants |
| 8 | Error analysis | Plots and explanations complete |
| 9 | Cycle model (optional) | Predicted vs. measured cycles |
| 10 | Report and demo | Submitted |

## 13. Risks and Mitigations

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| Array size exceeds available time | Medium | Week 3 gate: shrink to a smaller tile, keep the same dataflow |
| Second variant doesn't finish | Medium | Week 6 gate: report the first variant fully, describe the second as planned |
| Timing closure fails at target clock | Medium | Relax target clock; report achieved fmax honestly |
| Bit-exact mismatch from golden model | Medium | Debug at PE level first; the golden model is the source of truth |
| No board available | Low–Medium | Simulation and synthesis only; state this in the report |
| Model export errors (wrong layout, transposed weights) | Medium | Check shapes and a known output before running the full layer |
| Scope creep into attention or KV cache | High | Non-goals are fixed; route ideas to Future Work |

## 14. Dependencies and Tools

- Python with PyTorch or Hugging Face Transformers (export and reference)
- cocotb and a Verilog simulator (Icarus or Verilator)
- Vivado or Yosys/OpenROAD for synthesis
- Board and toolchain only if bring-up is attempted
- Git for versioning, with a log file of decisions and surprises

## 15. Open Questions

- [ ] Which model and layer? (Decide by end of Week 1)
- [ ] Which design decision? (Decide by end of Week 1)
- [ ] Which synthesis target and board, if any?
- [ ] Exact start and end dates, and any other commitments that overlap?

## 16. Future Work (Out of Scope)

- Softmax approximation and attention accelerator
- Tiled, FlashAttention-style attention
- KV-cache streaming subsystem
- Multi-layer or end-to-end token generation
