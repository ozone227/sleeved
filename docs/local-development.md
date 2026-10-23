# Local Development

This sets up a full local environment on **macOS** or **Linux/WSL2**. The
first run is dominated by downloading tools and container images; once the
cluster exists, rerunning `make dev-up` takes seconds.

## What you get

A small local Kubernetes cluster that mirrors production (the `nemesis` k3s
cluster), with the app code running directly on your machine for fast reloads.

```mermaid
flowchart LR
    subgraph host["Your machine (macOS or Linux/WSL2)"]
        direction TB
        browser["Browser / curl"]
        scripts["scripts/*.py<br/>(.venv)"]
        app["Gallery app (Vite) and backend API<br/>planned, run with npm / on host"]
    end

    subgraph docker["Docker (Docker Desktop / OrbStack / Colima / Engine)"]
        direction TB
        lb["k3d load balancer<br/>host :8080"]
        subgraph k3s["k3d cluster 'sleeved-dev' - k3s v1.34, same minor as prod"]
            direction TB
            traefik["Traefik<br/>(bundled with k3s)"]
            subgraph ns["namespace: sleeved"]
                s3["s3 - moto server<br/>bucket sleeved-collection<br/>versioning, public read, CORS<br/>in-memory"]
                pg[("postgres 17<br/>1Gi volume")]
            end
        end
    end

    browser -->|"http://sleeved-storage.localhost:8080"| lb
    scripts -->|"S3 API, path-style"| lb
    app -.->|"S3 API"| lb
    lb --> traefik
    traefik -->|"Host: sleeved-storage.localhost"| s3
    app -.->|"make dev-db<br/>port-forward :5432"| pg
```

Dashed lines are planned: `app/` and the backend API don't exist yet.

| Piece | Where it runs | Notes |
| --- | --- | --- |
| S3 stand-in ([moto](https://github.com/getmoto/moto) server) | in the cluster | Production storage is AWS S3, so locally we want faithful S3 *API* behavior. Bucket `sleeved-collection` is created with versioning, public read and CORS. In-memory; credentials aren't checked |
| Postgres 17 | in the cluster | For the planned multi-user backend ([plan](multi-user-architecture-plan.md)). Reached from the host with `make dev-db` |
| Traefik | in the cluster (bundled with k3s) | Same ingress controller and `traefik.io/v1alpha1` CRDs as prod |
| Gallery app (Vite), backend API | on your machine | Hot reload, no image rebuilds. Neither exists yet |
| `scripts/*.py` | on your machine | Python venv in `.venv/` |

Longhorn (prod's storage class) isn't installed locally; k3s's `local-path`
StorageClass stands in. The cluster is [k3d](https://k3d.io) (k3s in Docker).

## 1. Install prerequisites

You install two things yourself; everything else comes from the repo's pinned
toolchain.

**a. A Docker engine, running.**

| Platform | Install |
| --- | --- |
| macOS | OrbStack (`brew install --cask orbstack`), Docker Desktop, or Colima. Choose the **Docker** option, not Kubernetes: k3d brings its own cluster, and a second Kubernetes would only add another kubectl context |
| Windows | Use **WSL2** (Ubuntu). Either enable Docker Desktop's WSL integration, or install Docker Engine inside the distro |
| Linux | Docker Engine (`docker-ce`), with your user in the `docker` group |

Check: `docker info` prints server details without an error.

**b. [mise](https://mise.jdx.dev)**, which installs Node, Python, kubectl and k3d at the versions pinned in [`mise.toml`](../mise.toml).

```bash
brew install mise                  # macOS
curl https://mise.run | sh         # Linux / WSL

# activate in your shell (use bash instead of zsh if that's your shell), then restart it
echo 'eval "$(mise activate zsh)"' >> ~/.zshrc
```

**c. `make`** — preinstalled with Xcode Command Line Tools on macOS;
`sudo apt install make` on Debian/Ubuntu/WSL.

**WSL only:** clone the repo inside the Linux filesystem (`~/src/sleeved`), not
under `/mnt/c`. File watching and Docker I/O are unusably slow there, and
`make doctor` will refuse. Ports published by the cluster are reachable from
your Windows browser at the same `localhost` URLs.

**Python/conda users:** you don't need conda for this project. Run
`conda deactivate` first so nothing shadows the project's `.venv`.

## 2. Set up the project

```bash
git clone git@github.com:ozone227/sleeved.git
cd sleeved
mise trust && mise install      # installs the pinned toolchain
make setup                      # Python deps into .venv
cp .env.example .env            # points scripts at the local S3 stand-in
make doctor                     # every line should show ✓
```

If `make doctor` prints a `✗`, it says how to fix it.

## 3. Start the environment

```bash
make dev-up
```

This creates the cluster (first run downloads the k3s, moto and Postgres
images), waits for Traefik, deploys the S3 stand-in and Postgres, and creates
the bucket. It ends with:

```
S3 API:   http://sleeved-storage.localhost:8080
Creds:    any (the stand-in does not check them)
Postgres: run 'make dev-db' for localhost:5432
```

`make dev-up` is idempotent; rerun it any time.

## 4. Verify it works

```bash
curl -s -o /dev/null -w '%{http_code}\n' -I http://sleeved-storage.localhost:8080/sleeved-collection
# 200
make dev-status                 # s3 and postgres pods should be Running / 1/1
```

Postgres, in a second terminal (the port-forward runs in the foreground):

```bash
make dev-db                     # leave running
# connect with: postgres://sleeved:sleeved-dev@localhost:5432/sleeved
```

Try the real workflow: add a card to the local bucket with `upload_card.py`
(it reads `.env`, so it targets the local stand-in, and prints `Target:` so you
can see where it's writing):

```bash
.venv/bin/python scripts/upload_card.py -i path/to/photo.jpg \
  --name "Test Card" --type Unit --color Red \
  --set "Welcome to Night City" --rarity Common --cost 1 --copies 1
```

To target real AWS S3 instead, temporarily move `.env` aside (it sets
`S3_ENDPOINT` and throwaway `AWS_*` credentials). Without `S3_ENDPOINT` the
script uses AWS S3 and your normal AWS credentials, as before.

Browse the bucket with the AWS CLI (there is no web console):

```bash
AWS_ACCESS_KEY_ID=dev AWS_SECRET_ACCESS_KEY=dev \
  aws --endpoint-url http://sleeved-storage.localhost:8080 s3 ls s3://sleeved-collection
```

`*.localhost` resolves to 127.0.0.1 in browsers and curl with no `/etc/hosts`
edits. If a tool on your machine doesn't resolve it, add
`127.0.0.1 sleeved-storage.localhost` to `/etc/hosts`.

## Day to day

| Command | Does |
| --- | --- |
| `make dev-status` | Pods, services, routes, volumes |
| `make dev-db` | Forward Postgres to `localhost:5432` (foreground) |
| `make dev-reset` | Wipe everything and rebuild from scratch |
| `make dev-down` | Delete the cluster and all its data (it's throwaway) |
| `make help` | List targets |

Interactive tools need the context named explicitly, e.g.
`k9s --context k3d-sleeved-dev`.

## Safety: this never touches production

Every `kubectl` call in the `Makefile` is pinned to the `k3d-sleeved-dev`
context. If you run your own commands, do the same:
`kubectl --context k3d-sleeved-dev ...`. Your default context may well be the
real cluster, and `make dev-up` deliberately does not switch it (it creates the
cluster with `--kubeconfig-switch-context=false`). Credentials in `dev/` and
`.env.example` are throwaway and local only; production credentials never live
in this repo.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `make doctor`: docker daemon not reachable | Start OrbStack / Docker Desktop / Colima (`sudo service docker start` on WSL) |
| `make doctor`: tool not found | Open a new shell after activating mise, then `mise install` |
| `make doctor`: port 8080 in use | Free the port; the cluster publishes Traefik there |
| `make doctor`: repo is under `/mnt/...` | WSL only; re-clone into `~/` |
| `ModuleNotFoundError: boto3` | Run `make setup`; deactivate conda first |
| Connection closed / refused right after `dev-up` starts | Traefik is still starting; `dev-up` waits for it, so rerun `make dev-up` |
| `NoSuchBucket` on every request | `passHostHeader: false` was removed from `dev/k8s/ingress.yaml` (see below) |
| Uploaded test images are gone | The S3 stand-in is in-memory; it resets on pod restart and `make dev-reset`. `make dev-up` re-seeds an empty `inventory.json` and `games.json` |
| k9s / kubectl can't connect | They're using your default (prod) context; pass `--context k3d-sleeved-dev` |
| Anything else strange | `make dev-reset` |

## Known gaps

- The S3 stand-in doesn't enforce credentials or bucket-policy authorization,
  so a policy mistake that would block anonymous reads on real S3 won't show up
  locally.
- Moto treats `anything.localhost` as a virtual-hosted bucket name, so the
  Traefik route sets `passHostHeader: false` (see `dev/k8s/ingress.yaml`).
  Don't remove it.
- `.env` is read by `scripts/upload_card.py` (via a small built-in loader that
  never overrides variables already set in your shell). `make` and the cluster
  don't use it. `app/` and the backend API don't exist yet; when they do, they
  run on the host (`npm run dev`) and should read `.env` too; the OAuth dev-app credentials are yours
  to create (redirect URI in `.env.example`).
- Tested end to end on macOS (Apple silicon, OrbStack). Not yet run on
  Linux/WSL2; the first contributor there should fix up anything that drifts.
- Unrelated to local dev: the MinIO chart used by `nemesis_k3s/minio-loki`
  pulls `quay.io/minio/*` images that no longer exist in the registry, so that
  deployment may only be running from a cached image.
