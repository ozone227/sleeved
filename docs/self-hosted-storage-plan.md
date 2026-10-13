# Self-Hosted Storage Plan (k8s + MinIO)

Status: **planned, not yet implemented**. This supersedes the GitHub Pages +
AWS S3 deployment model described elsewhere in this repo. Once implemented,
`docs/architecture.md`, `CLAUDE.md`, and the S3-specific scripts should be
updated to match.

## Decision

- **Deployment**: move off GitHub Pages onto the self-hosted `nemesis` k3s
  cluster.
- **Storage**: move off AWS S3 onto a self-hosted, S3-API-compatible object
  store (MinIO) running in that same cluster, so `upload_card.py` and the
  gallery app keep using the S3 API with only an endpoint/credential swap.

## Why MinIO, and why standalone (not distributed)

- The existing codebase (`scripts/upload_card.py`, `scripts/setup-bucket.sh`)
  is built entirely around the S3 API via boto3 — bucket policies, public-read,
  versioning, content-type headers. MinIO is a drop-in S3-API replacement, so
  this is an endpoint swap, not a rewrite.
- The `nemesis` cluster already runs a proven MinIO pattern: `minio-loki` (in
  the GitOps repo `ozone227/nemesis_k3s`), standalone mode, backed by a single
  Longhorn PVC. This plan mirrors that pattern.
- The cluster's `longhorn` StorageClass already replicates every PVC 3x across
  nodes. Running MinIO's own distributed/erasure-coded mode on top of that
  would double up redundancy for no benefit (MinIO's distributed mode is
  designed for direct-attached JBOD disks, not for sitting on a replicated
  block store) — so standalone MinIO on one Longhorn PVC is the right call,
  not a compromise.

## Why public internet exposure is fine here

- The gallery is meant to be publicly browsable (same intent as the original
  GitHub Pages design), not just reachable on the home network.
- The cluster already has public inbound access and a working ACME setup:
  Traefik's `letsencrypt` certresolver uses Route53 DNS-01 challenges, and
  the existing Minecraft server ingress proves ports are already reachable
  from the internet. Exposing Sleeved's storage publicly is a new `Host`
  rule, not new infrastructure.

## Concrete plan

**In `ozone227/nemesis_k3s` (GitOps repo):**

1. New chart directory `minio-sleeved/`, modeled directly on `minio-loki/`:
   - Dependency on the official `charts.min.io` MinIO chart (same version
     pinned by `minio-loki`, currently 5.4.0).
   - `mode: standalone`, one Longhorn-backed PVC (`storageClass: longhorn`),
     starting at **20Gi** (card photos are small; `longhorn` supports volume
     expansion, so grow later rather than over-provisioning now).
   - `existingSecret: minio-sleeved-credentials` — never store credentials
     in git. Created manually before the first ArgoCD sync, same as
     `minio-loki-credentials`:
     ```
     kubectl create secret generic minio-sleeved-credentials -n sleeved \
       --from-literal=rootUser=<ACCESS_KEY> \
       --from-literal=rootPassword=<SECRET_KEY>
     ```
   - One bucket, `sleeved-collection` (same name as the current S3 bucket),
     provisioned with **`policy: download`** (MinIO's public-read-only
     policy — equivalent to the current S3 public-read ACL).
   - `ingress.enabled: false` / `consoleIngress.enabled: false` — exposed via
     custom Traefik `IngressRoute`s instead, matching `minio-loki`'s pattern
     (HTTP→HTTPS redirect Middleware + HTTPS route with
     `tls.certResolver: letsencrypt`).
   - Hostnames: `sleeved-storage.nemesis.drbond.net` (S3 API),
     `sleeved-storage-console.nemesis.drbond.net` (admin console). This
     leaves `sleeved.nemesis.drbond.net` free for the gallery app itself.
2. New namespace `sleeved` — dedicated, not shared with `observability`. This
   app is public-facing and distinct from internal log storage, so it gets
   its own namespace/credentials/blast radius.
3. New ArgoCD `Application` at `argocd/applications/minio-sleeved.yaml`,
   `destination.namespace: sleeved`, `syncOptions: [CreateNamespace=true]`,
   same retry/backoff policy as the other apps in this repo.

**In this repo (`sleeved`):**

4. Update `docs/architecture.md` and `CLAUDE.md`: base URL becomes
   `https://sleeved-storage.nemesis.drbond.net/sleeved-collection/...`
   (MinIO path-style, not S3 virtual-hosted-style), bucket layout underneath
   stays identical (`games.json`, `{game-id}/inventory.json`,
   `{game-id}/legends|units|programs|gear/...`).
5. Update `scripts/upload_card.py`'s boto3 client to point `endpoint_url` at
   the new MinIO host and use MinIO access/secret keys instead of AWS IAM
   credentials.
6. Retire `scripts/setup-bucket.sh` — bucket creation/policy is now declared
   in `minio-sleeved/values.yaml` and managed by ArgoCD instead of a one-time
   imperative script.

## Follow-up (not blocking initial deploy)

- Bucket **versioning** isn't one of the MinIO Helm chart's bucket-
  provisioning options. Enable it once, post-deploy, via the `mc` CLI
  (`mc version enable sleeved-storage/sleeved-collection`) against the new
  endpoint.
- Revisit the `app/` gallery's own public hostname (`sleeved.nemesis.drbond.net`)
  and its Traefik `IngressRoute` once that app exists.
