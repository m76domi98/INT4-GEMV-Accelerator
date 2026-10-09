# Decision Log

Append-only. One row per decision or surprise, newest last. Do not rewrite old rows; add a new row that supersedes one.

Types: **decision** (a choice made), **surprise** (something that did not match the expectation), **gate** (a PLAN.md gate outcome), **negative** (a failed approach or result, kept on purpose).

| Date | Stage | Type | Entry | Why / evidence | Revisit by |
| --- | --- | --- | --- | --- | --- |
| 2026-10-09 | 0 | decision | Plan organized by PRD milestones, one design doc per stage | PRD §12 already defines stage boundaries and exit criteria | Week 1 review |
| 2026-10-09 | 0 | decision | Recommend Yosys/OpenROAD as synthesis flow, Vivado as fallback | Scriptable and reproducible from a clean checkout (PRD §9); Vivado depends on a license install | Stage 5 start |
| 2026-10-09 | 1 | decision | Recommend per-channel requantization as the chosen design decision | G3 asks about outlier channels; per-channel scales make that error visible. See [01-spec-golden](design/01-spec-golden.md) | Week 1 spec freeze |
| 2026-10-09 | 1 | decision | Model: SmolLM2-135M (Apache-2.0), chosen over Qwen2.5-0.5B | Smaller for fast iteration. Config: hidden 576, FFN 1536, 30 layers. License read from model card; re-check before freezing | Stage 1 freeze |
| 2026-10-09 | 1 | decision | Layer: `model.layers.15.mlp.up_proj`, shape [1536, 576] | Largest MLP matrix; middle layer. Do not switch | Stage 1 freeze |
| 2026-10-09 | 1 | decision | Requant: per-channel as the variant, per-tensor as the comparison. Fixed-point `M_r` with shift 15 | Standard in practice; error analysis needs per-row variation | Stage 1 freeze |
| 2026-10-09 | 1 | decision | Accumulator: signed 21-bit, from worst case 1016 × 576 = 585,216 | Worst-case width fixed for the spec. Narrower width checked against real weights in Stage 6 (prediction P3: 18 bits) | Stage 6 |
| 2026-10-09 | 5 | decision | Synthesis: Yosys + OpenROAD, pending instructor check | Free and scriptable. Vivado only if the course requires it | Week 2 (instructor reply) |
| 2026-10-09 | 5 | decision | Supersedes the row above: Synthesis is Yosys + OpenROAD with no instructor check. Vivado only if already installed | Project is self-directed, not a course project, so no course requirement applies | Stage 5 start |
| 2026-10-09 | 0 | decision | Simulator: Icarus Verilog 14.0 under WSL (Linux). Verilator is the alternate (`make test SIM=verilator`) | Icarus is not installed on Windows. WSL gives a working Linux toolchain with the same make flow | Stage 2 start |
| 2026-10-09 | 0 | decision | Python 3.12 (uv-managed venv in WSL home, not on /mnt/c). Pins: cocotb 1.9.2, numpy 2.1.3, torch 2.5.1, transformers 4.46.3 | Default Python 3.14 has no wheels for numpy 2.1.3 or torch 2.5.1, so numpy built from source and failed. Venv on the Windows drive was too slow | Stage 1 start |
| 2026-10-09 | 0 | surprise | `pip install` on Python 3.14 and WSL network failures (VPN) blocked setup | Torch pulls about 2.5 GB of CUDA packages on Linux. The project does not use a GPU, so a CPU torch build is a possible later change | Stage 1 start |
