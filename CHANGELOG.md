# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Project scaffold: `src/` package layout, tests, evaluation folders, and CI with ruff, strict mypy and pytest.
- Apache-2.0 licence.
- Detector protocol and lane result contract, a lane registry built from `picopike.toml`, and an append-only JSONL trace (schema 1, hash-only by default).
- Input normalizer that strips invisible and format characters, folds look-alike letters and decodes base64, hex and rot13 payloads in place, with stated work bounds, completeness reporting and property tests.
- Rules-based hard guard that scans the raw and normalized text and reports evidence rather than a probability. Full chat-template role headers, judge-envelope forgeries and incompletely inspected input are never allowed; other structural, phrase and obfuscation signals are reported for later stages.

### Changed

- CI uses `actions/checkout` v7 and `astral-sh/setup-uv` v7.
