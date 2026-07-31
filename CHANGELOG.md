# Changelog

All notable public changes are recorded here. This project follows
[Semantic Versioning](https://semver.org/). Released versions are tagged and receive a GitHub
Release; the historical v0.6.0 entry below records the versioned git state before that workflow
existed.

## [Unreleased]

### Added

- Guided configuration now separates observed local facts from deterministic inferred candidates,
  confidence/evidence, and unresolved operator decisions.
- Candidates cover a filename-year edition, repeated edge-page labels, exact semantic section
  markers, OCR policy, and coarse layout characteristics. They are never silently applied as
  profile authority.
- Documented release procedure for version, validation, annotated tag, and GitHub Release.

## [0.6.0] - 2026-07-31

### Added

- Authorization-gated guided local inspection for PDF, text, and Markdown sources, with no-write
  metadata-only profile proposals, OCR readiness, unresolved decisions, and reproducible next
  commands. ([d78ab1a](https://github.com/BTCElectrician/elec-codebook-oo/commit/d78ab1a2e8006553db729b368b31c38fda1aa712))

### Fixed

- Current hosted Ruff compatibility after the guided configuration addition.
  ([8981696](https://github.com/BTCElectrician/elec-codebook-oo/commit/8981696511883221b5bc9cf3a4a838d3457c17cd))

[Unreleased]: https://github.com/BTCElectrician/elec-codebook-oo/compare/8981696511883221b5bc9cf3a4a838d3457c17cd...HEAD
[0.6.0]: https://github.com/BTCElectrician/elec-codebook-oo/compare/d78ab1a2e8006553db729b368b31c38fda1aa712...8981696511883221b5bc9cf3a4a838d3457c17cd
