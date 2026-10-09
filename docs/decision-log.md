# Decision Log

Append-only. One row per decision or surprise, newest last. Do not rewrite old rows; add a new row that supersedes one.

Types: **decision** (a choice made), **surprise** (something that did not match the expectation), **gate** (a PLAN.md gate outcome), **negative** (a failed approach or result, kept on purpose).

| Date | Stage | Type | Entry | Why / evidence | Revisit by |
| --- | --- | --- | --- | --- | --- |
| 2026-10-09 | 0 | decision | Plan organized by PRD milestones, one design doc per stage | PRD §12 already defines stage boundaries and exit criteria | Week 1 review |
| 2026-10-09 | 0 | decision | Recommend Yosys/OpenROAD as synthesis flow, Vivado as fallback | Scriptable and reproducible from a clean checkout (PRD §9); Vivado depends on a license install | Stage 5 start |
| 2026-10-09 | 1 | decision | Recommend per-channel requantization as the chosen design decision | G3 asks about outlier channels; per-channel scales make that error visible. See [01-spec-golden](design/01-spec-golden.md) | Week 1 spec freeze |
