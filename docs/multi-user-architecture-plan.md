# Multi-User Architecture Plan

Status: **planned, not yet implemented**. This partially supersedes the
current single-owner, no-auth design described in `CLAUDE.md` and
`docs/architecture.md`. It does not change the self-hosted object storage
plan in `docs/self-hosted-storage-plan.md` — card images stay in MinIO
regardless of this decision.

## Context

Designing the Trading List feature (see `docs/features/trading-list.md`)
surfaced per-user mutable state — keep-target overrides, trading-list
check-offs — that ought to sync across devices. That, plus a decision that
multi-user support (other collectors running their own Sleeved collection,
not just the original owner) is a near-term goal and not a someday-maybe,
means Sleeved needs real accounts and a backend, not just a bigger bucket.

## Decision

- **Auth**: OAuth2 "Sign in with Discord" and "Sign in with Google." A
  small backend API implements both providers' standard OAuth2 flows,
  matches or creates a local user record from the provider profile, and
  issues its own session (cookie or JWT). No self-hosted identity provider
  (Authelia, Keycloak) — that's real infrastructure for a user count this
  app doesn't have, and "social login" against providers collectors already
  have accounts with is simpler for everyone.
- **Database**: self-hosted Postgres in the `nemesis` k8s cluster (Helm
  chart + Longhorn PVC, same GitOps pattern as `minio-loki`), for
  everything that is genuinely per-user and relational:
  - `users` (id, provider, provider_user_id, display name, created_at)
  - `inventory_entries` (user_id, card_id, copies) — replaces the
    single-owner `{game-id}/inventory.json` file for owned-copy data
  - `keep_target_overrides` (user_id, card_id, target)
  - `trading_list_checkoffs` (user_id, card_id, checked_at)
- **New backend API service**: mediates OAuth login and all Postgres
  reads/writes, and serves the card catalog and image URLs to the gallery
  app. The React/Vite app becomes an API client instead of fetching JSON
  directly from a public bucket with no backend at all.

## What stays where, and why

| Data | Where | Why |
| --- | --- | --- |
| Card images | MinIO (per `self-hosted-storage-plan.md`) | Blobs; object storage is exactly right for this, unaffected by the auth/multi-user decision. |
| Per-game card catalog (`games/{game-id}.json`, `{game-id}.cards.json`) | Git, versioned | Identical for every user of that game — no multi-tenancy needed. Reviewable via PR when a new set releases, same as adding a game today. |
| Owned inventory, keep targets, check-offs | Postgres | Per-user, needs safe concurrent writes across different users, needs to sync across a user's own devices, and sets up cross-user queries (trade matching, listed as "later" in the Trading List spec) as ordinary SQL joins instead of a one-off. |

This is the same "don't reach for a database until you have a problem a
database actually solves" reasoning as before — the difference is that
multi-user *is* that problem. A single owner's flat JSON files were never
the bottleneck; concurrent, per-account mutable state is.

## Why this doesn't change the storage migration plan

`docs/self-hosted-storage-plan.md` is about where card *images* and the
public, read-only parts of the catalog live (self-hosted MinIO instead of
S3). That's orthogonal to who's allowed to write what, and proceeds as
already planned. This doc only changes the *owned inventory* side of things
— which was previously also flat JSON in the bucket, and now moves to
Postgres because it's no longer single-owner data.

## Open questions and follow-up

- [ ] Backend API service: hosting/stack choice (language/framework) —
  deliberately out of scope here.
- [ ] Migration path for the existing single-owner inventory data into
  Postgres as the first `users` row.
- [ ] Does read-only gallery browsing stay anonymous/public, or does
  viewing anyone's collection also require an account?
- [ ] Session mechanism specifics (JWT vs. server-side session + cookie).
