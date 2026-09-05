# The TCG Nexus v0.1.0

A multi-game trading card collection manager and gallery.

## Structure

```
tcg-nexus/
├── scripts/        # Infra setup and utility scripts
├── schema/         # JSON schemas for inventory files
├── games/          # Per-game configuration
├── docs/           # Architecture decisions and notes
└── app/            # Gallery web app (React + Vite) — coming soon
```

## Storage

Card images and inventory data live in S3:

- **Bucket**: `tcg-nexus-collection` (us-east-1)
- **Public URL**: `https://tcg-nexus-collection.s3.amazonaws.com`
- **Structure**: `s3://tcg-nexus-collection/{game-id}/{type}/{color?}/{card-slug}.jpg`
- **Inventory**: `s3://tcg-nexus-collection/{game-id}/inventory.json`
- **Games manifest**: `s3://tcg-nexus-collection/games.json`

## Supported Games

- [Cyberpunk TCG](games/cyberpunk-tcg.json)

## Scripts

- `scripts/setup-bucket.sh` — Create and configure the S3 bucket
- `scripts/upload-card.sh` — Upload a card image and update inventory *(coming soon)*
