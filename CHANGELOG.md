# Changelog

All notable public changes are recorded here. This project follows
[Semantic Versioning](https://semver.org/). Released versions are tagged and receive a GitHub
Release; the historical v0.6.0 entry below records the versioned git state before that workflow
existed.

## [Unreleased]

### Fixed

- Article/section identity now comes only from a heading on a chunk's first line. Before this,
  a chunk could be labeled from a number-led sentence (`1.25 times ...`), a prose reference
  (`Article 4 requirements ...`), the first word of a length-split continuation, or the previous
  article's last section after a new article began. A heading inside a single-newline paragraph
  now starts its own chunk instead of hiding under the earlier section's label.
- Running headers, footers, and page numbers repeated at nearby page edges are no longer indexed
  as chunks or used as identity. Page evidence keeps them; `"page_furniture": "off"` restores the
  old behavior.
- Identical chunks with the same identity (for example a page duplicated in a scan) are indexed
  once, with the other locations in `metadata.duplicate_locations` and the citation.
- Document ids no longer include a corpus-wide chunk counter or the source hash, so an edit on one
  page leaves the ids on other pages unchanged. pgvector re-ingest now handles a stable id moving
  to a new `chunk_number` without violating the per-corpus uniqueness constraint, and rejects
  duplicate ids or chunk numbers before connecting.
- Local ingest writes `documents.json` and `pages.json` as one unit; a failure while writing no
  longer leaves new documents beside old page evidence.

### Changed

- Document schema version 2.3 (new id derivation; `metadata.identity_source`,
  `metadata.identity_version`, `metadata.duplicate_locations`, and per-page
  `furniture_lines_removed`). Re-ingest existing corpora to adopt it.
- Default models now live in `codebook_agent/model_defaults.py`: OCR correction `gpt-6-luna`
  (was `gpt-5.6-terra`), answer synthesis `gpt-6.1-sol` (was `gpt-5.6-terra`), embeddings
  `text-embedding-3-small` (unchanged). Bundled profiles inherit the correction default instead
  of pinning a model, and `capabilities --json` reports `default_models`.
- Raised dependency floors for untrusted-input parsers: `pypdf>=6.0`, `pillow>=10.3`.
- CI runs on Python 3.11 and 3.13.

## [0.7.0] - 2026-07-31

### Added

- Guided configuration now separates observed local facts from deterministic inferred candidates,
  confidence/evidence, and unresolved operator decisions.
- Candidates cover a filename-year edition, repeated edge-page labels, exact semantic section
  markers, OCR policy, and coarse layout characteristics. They are never silently applied as
  profile authority.
- Documented release procedure for version, validation, annotated tag, and GitHub Release.

### Changed

- The profile-proposal machine contract is now version 1.2 and explicitly includes the
  `configuration_assessment` review packet.

## [0.6.0] - 2026-07-31

### Added

- Authorization-gated guided local inspection for PDF, text, and Markdown sources, with no-write
  metadata-only profile proposals, OCR readiness, unresolved decisions, and reproducible next
  commands. ([d78ab1a](https://github.com/BTCElectrician/elec-codebook-oo/commit/d78ab1a2e8006553db729b368b31c38fda1aa712))

### Fixed

- Current hosted Ruff compatibility after the guided configuration addition.
  ([8981696](https://github.com/BTCElectrician/elec-codebook-oo/commit/8981696511883221b5bc9cf3a4a838d3457c17cd))

[Unreleased]: https://github.com/BTCElectrician/elec-codebook-oo/compare/v0.7.0...HEAD
[0.7.0]: https://github.com/BTCElectrician/elec-codebook-oo/releases/tag/v0.7.0
[0.6.0]: https://github.com/BTCElectrician/elec-codebook-oo/compare/d78ab1a2e8006553db729b368b31c38fda1aa712...8981696511883221b5bc9cf3a4a838d3457c17cd
