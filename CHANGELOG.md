# Changelog

All notable changes to this project are recorded here by stage. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Entries are added when a stage's exit criterion is met, or when a decision changes the plan.

## [Unreleased]

### Added

- Project plan with stages, gates, and working agreements ([docs/PLAN.md](docs/PLAN.md)), derived from PRD Draft v1.
- Design doc stubs for every stage, Stage 0 through Stage 8 ([docs/design/](docs/design/)).
- Decision log for choices and surprises ([docs/decision-log.md](docs/decision-log.md)).
- Stage 1 spec: SmolLM2-135M, `layers.15.mlp.up_proj`, per-channel requantization, 21-bit accumulator, error bound formula, and Week 1 predictions ([docs/design/01-spec-golden.md](docs/design/01-spec-golden.md)).
- Stage 1 exit: versioned export script with shape and known-output checks, integer golden model, and bound check. Per-channel stays within the frozen error bound on every calibration and test vector. P1, P2, and P3 pass. Results are in the spec, and the requantization saturation surprise is logged ([docs/decision-log.md](docs/decision-log.md)).
