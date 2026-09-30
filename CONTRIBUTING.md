# Contributing

Thanks for helping. PicoPike is pre-alpha, so interfaces may still change; open an issue before starting anything large.

## Setup

Requires Python 3.13 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Checks

CI runs the following; run them locally before opening a pull request.

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run mypy tools
uv run python -m tools.logo check
uv run pytest
```

Tests that load models, touch the network, or need datasets are marked `integration` and are skipped in CI. Run them locally with `uv run pytest -m integration`.

## Branches and commits

- Branch from `main` as `feature/<short-description>` or `bug/<short-description>`, in kebab case.
- Write commit subjects in the imperative mood, under about 70 characters: `Add per-language temperature scaling`.
- Keep each pull request to one concern. Update `CHANGELOG.md` under **Unreleased** when behaviour changes.

## Dependencies

Add dependencies with `uv add` (or `uv add --dev` for tooling) and commit the updated `uv.lock`. CI installs with `uv sync --locked` and fails if the lockfile is stale.

## Data and models

Never commit datasets, model weights, or traces containing prompt text. `evals/datasets/`, `evals/reports/` and weight files are ignored for that reason. Respect each dataset's licence; datasets with non-commercial terms are not used.

## Logo and brand assets

The logo SVGs in `assets/` are built from `brand/logo.spec.json`; do not edit them by hand.

```bash
uv run python -m tools.logo build    # rebuild the SVGs from the spec
uv run python -m tools.logo export   # favicons and social preview PNGs (needs Inkscape)
```
