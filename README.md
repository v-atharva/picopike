<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.svg">
  <img src="assets/logo.svg" alt="PicoPike" width="380">
</picture>

**Tiny classifier. Outsized sting.**

Prompt-injection, jailbreak and harmful-request detection for LLM inputs.
A small local model screens every request in milliseconds; a larger judge is consulted only when it is unsure.

[![CI](https://github.com/v-atharva/picopike/actions/workflows/ci.yml/badge.svg)](https://github.com/v-atharva/picopike/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.13-3776AB?logo=python&logoColor=white)
![Status](https://img.shields.io/badge/status-pre--alpha-orange)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

[Overview](#overview) ·
[Architecture](#architecture) ·
[Getting started](#getting-started) ·
[Benchmark](#benchmark) ·
[Roadmap](#roadmap)

</div>

---

## Overview

PicoPike sits in front of a language model and decides whether an incoming prompt is safe to pass on. It is built as a cascade, so the expensive step only runs when it is needed:

1. **Rules** catch the obvious cases deterministically, in well under a millisecond.
2. **The pike model**, a compact multilingual encoder with calibrated heads, scores every request on a laptop CPU in single-digit milliseconds.
3. **An LLM judge** is called only when the pike model's score falls inside an uncertainty band.

The lane outputs are fused into one calibrated probability and an `ALLOW`, `HOLD` or `BLOCK` decision. Every step, with its raw output, timing and cost, is written to a JSONL trace.

> **Status: pre-alpha.** The repository, tooling and CI are in place. The detectors, benchmark and API described below are being built; nothing here is ready for production traffic.

## Why another detector

Strong open guard models already exist. What is missing is evidence that holds up outside English and under attack:

- **Calibrated in every language.** Scores are temperature-scaled per language, so a threshold means the same thing in English, Russian and Chinese.
- **Honest under attack.** The benchmark reports calibration on adaptively attacked prompts, not only on clean ones.
- **Cheap by default.** Most traffic never leaves the machine; the judge is a fallback, not the main path.
- **Benchmark first.** Every detector, including PicoPike, is a row in the same multi-axis leaderboard. If a larger baseline wins on accuracy, the report says so and shows the latency and cost trade-off.

## Architecture

```text
request ─▶ api      POST /v1/classify {text, mode, lang?}
             │
             ▼
           router   1. rules          deterministic        ~0.1 ms   free
                    2. pike           local model, always  ~5 ms     free
                    3. judge          only when uncertain  ~1-2 s    metered
                    4. fusion         stacker + calibration → score, decision
             │
             ▼
           trace    JSONL: every lane's output, timings and cost

offline:   bench    datasets → adaptive attacks → cached detector runs → metrics → leaderboard
           train    pike heads · fusion stacker · per-language calibration
```

Two serving modes: `fast` runs rules and the pike model only; `auto` adds the judge for uncertain requests, within a budget guard. A lane that fails or times out degrades the result explicitly and never fails the request.

## Getting started

Requires Python 3.13 and [uv](https://docs.astral.sh/uv/).

```bash
git clone git@github.com:v-atharva/picopike.git
cd picopike
uv sync
uv run pytest
```

The command line (`picopike serve`, `picopike bench run`, `picopike bench report`) arrives with phase 1.

## Benchmark

No results yet. The leaderboard will be produced by `picopike bench report` from cached detector runs, so every number in it is reproducible without re-spending API budget.

| Axis | What is measured |
|---|---|
| Detection | AUROC, F1 at the policy threshold, FPR at 95% TPR |
| Over-defense | Share of safe-but-suspicious prompts that are blocked |
| Calibration | Expected calibration error on clean and on attacked prompts |
| Speed and cost | p50 and p99 latency on an Apple M2 CPU; cost per 1,000 decisions |
| Breakdown | Per dataset and per language (English, Russian, Chinese) |

Evaluation sets are held out from training, near-duplicates are removed, and the report prints the remaining train/test overlap. Datasets keep their own licences and are never redistributed from this repository.

## Project layout

```text
.
├── src/picopike/   the library: detectors, fusion, API, trace
├── tests/          unit tests (CI) and integration tests (local, -m integration)
├── evals/          benchmark datasets and reports (contents are not committed)
├── brand/          logo spec and bundled fonts
├── tools/          repository tooling, including the logo builder
├── assets/         logo, icons, favicons and the social preview
└── scripts/        developer utilities
```

## Roadmap

- [ ] **Phase 1: detect and measure.** Detector protocol, rules, the pike model, the LLM judge, fusion and calibration, the serving API, and the multi-axis benchmark with adaptive attacks.
- [ ] **Phase 2: review and improve.** A review dashboard for held decisions, with a label-and-retrain loop.
- [ ] **Phase 3: watch the reasoning.** Monitoring the chain-of-thought of open reasoning models, not just their inputs.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, checks and conventions, and the [Code of Conduct](CODE_OF_CONDUCT.md).

## Security

Please report vulnerabilities, and inputs that get past the detector, as described in [SECURITY.md](SECURITY.md).

## License

Apache License 2.0; see [LICENSE](LICENSE). Datasets used by the benchmark keep their own licences and are not redistributed here. The bundled Inter font is under the SIL Open Font License ([brand/fonts/OFL.txt](brand/fonts/OFL.txt)).
