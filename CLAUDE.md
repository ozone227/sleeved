# Sleeved — Claude Code Context

A multi-game trading card collection manager and gallery. Built to catalog physical card collections via phone photography, store images and inventory data in AWS S3, and serve them through a public web gallery.

---

## Project Structure

```
sleeved/
├── CLAUDE.md                   ← you are here
├── CONTRIBUTING.md             # Branching model and semver policy
├── CHANGELOG.md                # Keep a Changelog, per package.json version
├── package.json                # Root project version (single source of truth)
├── scripts/
│   └── setup-bucket.sh         # One-time S3 bucket creation and configuration
├── schema/
│   └── inventory.schema.json   # JSON schema for per-game inventory files
├── games/
│   └── cyberpunk-tcg.json      # Game config: types, colors, sets, keywords, S3 paths
├── docs/
│   └── architecture.md         # Design decisions and storage layout
└── app/                        # React + Vite gallery app (in progress)
```

---

## Versioning & Branching

Full policy: [`CONTRIBUTING.md`](CONTRIBUTING.md). Summary for anything working in
this repo (including Claude Code sessions):

- **Branching (GitHub Flow)** — don't commit straight to `main` except trivial
  one-line doc fixes. Branch as `feature/`, `fix/`, or `chore/` for anything else
  (app work, schema/game-config changes, scripts), PR into `main`, then delete
  the branch.
- **Semantic versioning** — `package.json` `version` is the single version for
  the whole project. MAJOR = breaking schema/S3-layout/game-config change,
  MINOR = new game or feature (additive), PATCH = fixes/docs/refactors.
- **Releasing** — bump `version`, move `CHANGELOG.md`'s `[Unreleased]` section
  into a dated `[X.Y.Z]` entry, update the version suffix on `README.md`'s title
  line (`# The TCG Nexus vX.Y.Z`), commit as `chore(release): vX.Y.Z`, tag `vX.Y.Z`.
- **`main` is branch-protected** — PRs required (no direct pushes, no force-push,
  no deletion), enforced for admins too. Always work on a branch.

---

## Storage: AWS S3

**Bucket**: `sleeved-collection`
**Region**: `us-east-1`
**Access**: Public read
**Versioning**: Enabled
**Base URL**: `https://sleeved-collection.s3.amazonaws.com`

### Bucket Layout

```
s3://sleeved-collection/
├── games.json                          # Top-level manifest of all supported games
└── {game-id}/
    ├── inventory.json                  # Card catalog for this game (see schema below)
    ├── legends/
    │   └── {card-slug}.jpg
    ├── units/{color}/
    │   └── {card-slug}.jpg
    ├── programs/{color}/
    │   └── {card-slug}.jpg
    └── gear/{color}/
        └── {card-slug}.jpg
```

Colors: `red`, `green`, `blue`, `yellow` (lowercase in S3 paths)

### Key S3 Commands

```bash
# List all files
aws s3 ls s3://sleeved-collection --recursive

# Upload a card image
aws s3 cp photo.jpg s3://sleeved-collection/cyberpunk-tcg/units/red/card-slug.jpg

# Fetch inventory
curl https://sleeved-collection.s3.amazonaws.com/cyberpunk-tcg/inventory.json

# Update inventory (after editing locally)
aws s3 cp inventory.json s3://sleeved-collection/cyberpunk-tcg/inventory.json \
  --content-type "application/json"
```

---

## Inventory Format

Card data lives in `{game-id}/inventory.json` in the bucket — **not** in this repo.
Schema is defined in `schema/inventory.schema.json`.

Key fields per card:
- `id` — URL-safe slug (e.g. `rogue-amerascu`)
- `type` — `Legend` | `Unit` | `Program` | `Gear`
- `color` — `Red` | `Green` | `Blue` | `Yellow` (null for Legends)
- `ram` — object with color keys, Legends only (e.g. `{"red": 2, "green": 1}`)
- `keywords` — array (e.g. `["Adrenaline", "Blocker"]`)
- `copies` — how many the owner has (1–3)
- `image` — relative S3 path within the game folder (e.g. `units/red/card-slug.jpg`)

---

## Game Configs

Each game is defined in `games/{game-id}.json`. This drives both the S3 folder
structure and the gallery app's filter UI. To add a new game:
1. Add `games/{new-game-id}.json` following the shape of `games/cyberpunk-tcg.json`
2. Create the S3 folder structure under `s3://sleeved-collection/{new-game-id}/`
3. Add an entry to `games.json` in the bucket root

---

## Gallery App (Planned)

**Stack**: React + Vite
**Hosting**: GitHub Pages (`https://ozone227.github.io/sleeved`)
**Location**: `app/` directory

Design principles:
- Config-driven per game — no hardcoded card types or colors
- Reads `games.json` and per-game `inventory.json` from S3 at runtime
- Filters by type, color, set, rarity, keyword
- No auth required — all assets are publicly readable from S3

---

## Supported Games

| Game | Config | S3 Prefix | Status |
|------|--------|-----------|--------|
| Cyberpunk TCG | `games/cyberpunk-tcg.json` | `cyberpunk-tcg/` | Active |

---

## Cyberpunk TCG Notes

For rules questions, card lookups, and deckbuilding help, use the `cyberpunk-tcg` skill.
It provides judge-level rules authority and accesses the live card database at
https://cyberpunktcg.com/cards.

Quick reference:
- **3 Legends** per deck (not counted in the 40–50 card main deck)
- **RAM** = color limits set by your Legend lineup
- **Win** by starting your turn with 7+ Gig Dice
- Card types: Legend, Unit, Program, Gear
- Colors: Red, Green, Blue, Yellow
- Keywords: Adrenaline, Blocker, Quick, Go Solo, Lag

---

## GitHub

**Repo**: https://github.com/ozone227/sleeved
**Owner**: ozone227 (Ryan Bond)
**Branch**: main
