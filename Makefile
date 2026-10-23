# Local development environment. See docs/local-development.md.
#
# Every kubectl call is pinned to the local k3d context so nothing here
# can ever touch the production `nemesis` cluster.

CLUSTER    := sleeved-dev
CTX        := k3d-$(CLUSTER)
NS         := sleeved

# Prefer the repo venv so this works regardless of shell activation.
PY := $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

KUBECTL := kubectl --context $(CTX)

.PHONY: help doctor dev-up dev-down dev-reset dev-status dev-db setup

help: ## Show targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

doctor: ## Check prerequisites (Docker, tools, WSL quirks)
	@scripts/dev/doctor.sh

setup: ## Install Python deps for scripts/ (run after `mise install`)
	$(PY) -m pip install -r requirements.txt

dev-up: doctor ## Create the local cluster and deploy S3 stand-in + Postgres (idempotent)
	@k3d cluster list $(CLUSTER) >/dev/null 2>&1 || k3d cluster create --config dev/k3d.yaml --kubeconfig-switch-context=false
	@$(KUBECTL) create namespace $(NS) --dry-run=client -o yaml | $(KUBECTL) apply -f -
	@echo "Waiting for k3s to install Traefik CRDs..."
	@for i in $$(seq 1 60); do $(KUBECTL) get crd ingressroutes.traefik.io >/dev/null 2>&1 && break; sleep 3; done
	@$(KUBECTL) wait --for=condition=established --timeout=60s crd/ingressroutes.traefik.io
	$(KUBECTL) apply -f dev/k8s/
	@$(KUBECTL) -n kube-system rollout status deploy/traefik --timeout=3m
	$(KUBECTL) -n $(NS) rollout status deploy/s3 --timeout=3m
	$(PY) scripts/dev/create-bucket.py
	$(KUBECTL) -n $(NS) rollout status statefulset/postgres --timeout=3m
	@echo
	@echo "S3 API:   http://sleeved-storage.localhost:8080"
	@echo "Creds:    any (the stand-in does not check them)"
	@echo "Postgres: run 'make dev-db' for localhost:5432"

dev-status: ## Show what is running in the local cluster
	$(KUBECTL) -n $(NS) get pods,svc,ingressroute,pvc

dev-db: ## Forward Postgres to localhost:5432 (foreground; Ctrl-C to stop)
	$(KUBECTL) -n $(NS) port-forward svc/postgres 5432:5432

dev-down: ## Delete the local cluster and all its data
	k3d cluster delete $(CLUSTER)

dev-reset: dev-down dev-up ## Wipe and recreate from scratch
