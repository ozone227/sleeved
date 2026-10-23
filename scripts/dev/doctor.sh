#!/usr/bin/env bash
# Verify the local-dev prerequisites. Exits non-zero with actionable messages.
set -u

fail=0
bad() { echo "✗ $1"; fail=1; }
ok()  { echo "✓ $1"; }

for tool in docker k3d kubectl node python3; do
  if command -v "$tool" >/dev/null 2>&1; then ok "$tool"; else
    case "$tool" in
      docker) bad "docker not found — macOS: install Docker Desktop, OrbStack, or Colima; WSL: enable Docker Desktop's WSL integration or install docker-ce in the distro" ;;
      *)      bad "$tool not found — install mise (https://mise.jdx.dev) and run 'mise install'" ;;
    esac
  fi
done

if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then ok "docker daemon reachable"; else
    bad "docker daemon not reachable — start Docker Desktop/OrbStack/Colima (or 'sudo service docker start' on WSL)"
  fi
fi

# WSL: the repo must live on the Linux filesystem, not /mnt/c (slow, breaks inotify/HMR).
if grep -qi microsoft /proc/version 2>/dev/null; then
  case "$PWD" in
    /mnt/*) bad "repo is under $PWD — clone it inside the WSL filesystem (e.g. ~/src) for usable performance" ;;
    *)      ok "WSL: repo is on the Linux filesystem" ;;
  esac
fi

# Port 8080 is the Traefik entrypoint published by k3d.
if ! k3d cluster list sleeved-dev >/dev/null 2>&1; then
  if (command -v lsof >/dev/null && lsof -iTCP:8080 -sTCP:LISTEN >/dev/null 2>&1); then
    bad "port 8080 is in use — free it before creating the cluster"
  else
    ok "port 8080 free"
  fi
fi

exit $fail
