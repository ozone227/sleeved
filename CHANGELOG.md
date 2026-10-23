# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versioning follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Local development environment: k3d cluster mirroring prod k3s with a moto S3
  stand-in and Postgres, `mise.toml` toolchain pins, `Makefile` targets, `make doctor`
  (see `docs/local-development.md`)
- `scripts/upload_card.py` honors `S3_ENDPOINT` / `S3_BUCKET` and loads `.env`,
  so it can target the local dev S3 stand-in; defaults to AWS S3 as before

## [0.1.0] - 2026-09-05

### Added

- Repo scaffold: `scripts/`, `schema/`, `games/`, `docs/`, `app/` structure
- S3 bucket setup script (`scripts/setup-bucket.sh`)
- Inventory JSON schema (`schema/inventory.schema.json`)
- Cyberpunk TCG game config (`games/cyberpunk-tcg.json`)
- Architecture notes (`docs/architecture.md`)
- `CLAUDE.md` project context for Claude Code
- Semantic versioning and GitHub Flow branching conventions (see `CONTRIBUTING.md`)

[Unreleased]: https://github.com/ozone227/sleeved/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ozone227/sleeved/releases/tag/v0.1.0
