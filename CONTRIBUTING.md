# Contributing

## Branching (GitHub Flow)

- `main` is always deployable and every release is tagged on it.
- Don't commit straight to `main` except for genuinely trivial, zero-risk changes
  (a typo, a one-line README/doc fix). Everything else — app features, bug fixes,
  schema or game-config changes, refactors, infra scripts — goes on a branch.
- Branch naming: `feature/<short-name>`, `fix/<short-name>`, `chore/<short-name>`
  (`docs/<short-name>` and `refactor/<short-name>` are fine too).
- Open a PR into `main` even when working solo — it's the record of what changed
  and why. Merge, then delete the branch.
- Tag releases on `main` as `vX.Y.Z`, matching the `version` in `package.json`.

## Semantic Versioning

`package.json` `version` is the single source of truth for the project's version,
covering the schema, game configs, scripts, and app together. Given `MAJOR.MINOR.PATCH`:

- **MAJOR** — breaking changes: fields removed/renamed in `schema/inventory.schema.json`,
  S3 bucket layout changes, incompatible changes to a game config's shape.
- **MINOR** — backward-compatible additions: a new game added under `games/`, a new
  app feature, a new optional schema field.
- **PATCH** — bug fixes, docs, refactors, non-breaking config tweaks, dependency bumps.

While the project is pre-1.0 (`0.y.z`), breaking changes may still land in a MINOR
bump — bump PATCH for fixes in the meantime. Move to `1.0.0` once the gallery app
has its first public release.

## Release Checklist

1. Merge the relevant PR(s) into `main`.
2. Bump `version` in `package.json`.
3. Move the `[Unreleased]` entries in `CHANGELOG.md` under a new
   `## [X.Y.Z] - YYYY-MM-DD` heading.
4. Commit: `chore(release): vX.Y.Z`.
5. Tag and push: `git tag -a vX.Y.Z -m "vX.Y.Z"` then `git push --tags`.

## Commit Messages

Prefer [Conventional Commits](https://www.conventionalcommits.org/) prefixes
(`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`) to keep history and future
changelogs easy to scan. Not enforced by tooling yet, just convention.
