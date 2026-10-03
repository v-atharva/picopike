<div align="center">

<h1>PicoPike</h1>

**Tiny classifier. Outsized sting.**

Prompt-injection, jailbreak and harmful-request detection for LLM inputs.
Designed so a small local model screens every request in milliseconds and a larger open-weight judge is consulted only when it is unsure.

[![CI](https://github.com/v-atharva/picopike/actions/workflows/ci.yml/badge.svg)](https://github.com/v-atharva/picopike/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.13-3776AB?logo=python&logoColor=white)
![Status](https://img.shields.io/badge/status-alpha-orange)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

[Overview](#overview) ·
[Architecture](#architecture) ·
[Getting started](#getting-started) ·
[Configuration](#configuration) ·
[Benchmark](#benchmark) ·
[Roadmap](#roadmap)

</div>

---

## Overview

PicoPike sits in front of a language model and decides whether an incoming prompt is safe to pass on. It is designed as a cascade, so the expensive step only runs when it is needed:

1. **Rules** run deterministically after undoing common obfuscation (invisible characters, look-alike letters, encoded payloads). Full chat-template role headers, judge-envelope forgeries and incompletely inspected input are never allowed; other structural, phrase and obfuscation signals feed the later stages. Typical prompts take about a tenth of a millisecond.
2. **The pike model**, a compact multilingual encoder with calibrated heads, will score every request on a laptop CPU, targeting single-digit milliseconds.
3. **An open-weight LLM judge** will be called only when the pike model's score falls inside an uncertainty band.

The lane outputs will be fused into one calibrated probability and an `ALLOW`, `HOLD` or `BLOCK` decision. Every step, with its raw output, timing and cost, will be written to a JSONL trace.

> **Status: alpha.** The detector interface, lane registry, configuration file, JSONL trace, input normalizer and rules-based hard guard are in place. The detectors, benchmark and API are being built and tested locally; nothing here is ready for production traffic.

## Why another detector

Strong open guard models already exist. What is missing is evidence that holds up outside English and under attack:

- **Calibrated, and honest about scope.** English comes first. Scores will be temperature-scaled per language, so adding Russian and Chinese later will not change what a threshold means.
- **Honest under attack.** The benchmark will report calibration on adaptively attacked prompts, not only on clean ones.
- **Cheap by default.** Most traffic will never leave the machine; the judge is a fallback, not the main path.
- **Open-weight throughout.** Every model PicoPike runs, including the judge, will have open weights and can be self-hosted.
- **Benchmark first.** Every detector, including PicoPike, will be a row in the same multi-axis leaderboard. If a larger baseline wins on accuracy, the report will say so and show the latency and cost trade-off.

## Architecture

This is the target design. Latencies are budgets, not measurements; the leaderboard will report measured numbers.

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

Two planned serving modes: `fast` runs rules and the pike model only; `auto` adds the judge for uncertain requests, within a budget guard. A lane that fails or times out will degrade the result explicitly and never fail the request.

## Getting started

Requires Python 3.13 and [uv](https://docs.astral.sh/uv/).

```bash
git clone git@github.com:v-atharva/picopike.git
cd picopike
uv sync
uv run pytest
```

The command line (`picopike serve`, `picopike bench run`, `picopike bench report`) arrives with phase 1.

## Configuration

`picopike.toml` at the repository root lists the detection lanes and where traces are written. By default a trace stores a SHA-256 of each input, not the text itself; set `store_text = true` under `[trace]` to keep the text on your own machine.

## Benchmark

No results yet. The leaderboard will be produced by `picopike bench report` from cached detector runs, so every number in it is reproducible without re-spending API budget.

| Axis | What is measured |
|---|---|
| Detection | AUROC, F1 at the policy threshold, FPR at 95% TPR |
| Over-defense | Share of safe-but-suspicious prompts that are blocked |
| Calibration | Expected calibration error on clean and on attacked prompts |
| Speed and cost | p50 and p99 latency on an Apple M2 CPU; cost per 1,000 decisions |
| Breakdown | Per dataset; English first, Russian and Chinese next |

Evaluation sets will be held out from training, near-duplicates removed, and the report will print the remaining train/test overlap. Datasets keep their own licences and are never redistributed from this repository.

## Project layout

```text
.
├── src/picopike/   the library: detector contract, registry, normalizer, hard guard, config and trace so far
├── tests/          unit tests (CI) and integration tests (local, -m integration)
├── evals/          benchmark datasets and reports (contents are not committed)
└── scripts/        developer utilities
```

## Roadmap

- [ ] **Phase 1: detect and measure (English).** Detector protocol, rules, the pike model, an open-weight LLM judge, fusion and calibration, a local serving API, and the multi-axis benchmark with adaptive attacks. Russian and Chinese follow once English is proven.
- [ ] **Phase 2: review and improve.** A review dashboard for held decisions, with a label-and-retrain loop.
- [ ] **Phase 3: watch the reasoning.** Monitoring the chain-of-thought of open reasoning models, not just their inputs.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, checks and conventions, and the [Code of Conduct](CODE_OF_CONDUCT.md).

## Security

Please report vulnerabilities, and inputs that get past the detector, as described in [SECURITY.md](SECURITY.md).

## License

Apache License 2.0; see [LICENSE](LICENSE). Datasets used by the benchmark keep their own licences and are not redistributed here.
