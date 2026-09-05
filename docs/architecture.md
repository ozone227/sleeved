# Architecture

## Storage: AWS S3

**Bucket**: `tcg-nexus-collection` (us-east-1)  
**Access**: Public read  
**Versioning**: Enabled

### Layout

```
s3://tcg-nexus-collection/
├── games.json                          # Top-level game manifest
└── {game-id}/
    ├── inventory.json                  # Card catalog for this game
    ├── legends/
    │   └── {card-slug}.jpg
    ├── units/{color}/
    │   └── {card-slug}.jpg
    ├── programs/{color}/
    │   └── {card-slug}.jpg
    └── gear/{color}/
        └── {card-slug}.jpg
```

### Design Decisions

- **Images and inventory co-located in S3** — no separate database; JSON files are the source of truth
- **Per-game `inventory.json`** — each game is self-contained; adding a game means adding a folder + config
- **Public read on objects** — gallery app fetches images directly from S3 without auth
- **Versioning enabled** — protects against accidental overwrites of images or inventory files

## App: React + Vite (planned)

- Config-driven per game (`games/` directory)
- Hosted on GitHub Pages
- Reads `games.json` and per-game `inventory.json` at runtime from S3

## Repo: GitHub (public)

- `scripts/` — infra and upload utilities
- `schema/` — JSON schema for inventory validation
- `games/` — per-game configuration
- `app/` — gallery web app
