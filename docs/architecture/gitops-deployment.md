# GitOps + Deployment (K3s + ArgoCD)

Target: Damian's homelab K3s (ARM64) with existing Postgres. LAN-only access via MetalLB LoadBalancer (no ingress needed).

## Repo structure (proposed)

```
.
├─ backend/                 # FastAPI app + scraper CLI entrypoints
├─ frontend/                # React dashboard
├─ k8s/
│  ├─ apps/
│  │  └─ madrid-rental-finder/
│  │     ├─ base/
│  │     │  ├─ namespace.yaml
│  │     │  ├─ api-deployment.yaml
│  │     │  ├─ api-service.yaml
│  │     │  ├─ dashboard-deployment.yaml
│  │     │  ├─ dashboard-service.yaml       # LoadBalancer (MetalLB .42)
│  │     │  ├─ cronjob-scrape-pisos.yaml
│  │     │  ├─ cronjob-scrape-yaencontre.yaml
│  │     │  ├─ cronjob-scrape-spotahome.yaml
│  │     │  ├─ configmap.yaml
│  │     │  └─ kustomization.yaml
│  │     └─ overlays/
│  │        └─ homelab/
│  │           ├─ kustomization.yaml
│  │           ├─ resources-patch.yaml
│  │           └─ secrets/ (SOPS or ExternalSecret, optional)
│  └─ argocd/
│     └─ madrid-rental-finder-app.yaml
└─ docs/
```

Use **Kustomize** (native to kubectl/ArgoCD) for simple overlays.

## Namespaces and ArgoCD project
- Namespace: `madrid-rental-finder`
- ArgoCD Project: use existing **data-services** (best fit) or `default`.

## Container images
- `dahomelab.azurecr.io/madrid-rental-finder/api:<tag>`
- `dahomelab.azurecr.io/madrid-rental-finder/scraper:<tag>` (can be same as api image if you expose a scraper CLI)
- `dahomelab.azurecr.io/madrid-rental-finder/dashboard:<tag>`

Tagging:
- `sha-<GITHUB_SHA>` for immutable deploys.
- Optional: `main` moving tag for convenience.

## Secrets and configuration

### Database credentials
Use the existing secret in namespace `postgresql`:
- `postgresql/postgresql-credentials`

Options:
1) **Best**: copy required keys into `madrid-rental-finder` namespace as a new secret (manual once), so workloads don't need cross-namespace secret access.
2) Advanced: ExternalSecrets operator (if installed) to mirror secrets.

Environment variables (API + scrapers):
- `DATABASE_URL=postgresql+psycopg://<user>:<pass>@postgresql.postgresql.svc.cluster.local:5432/madrid_rental_finder`
- `MRF_LOG_LEVEL=INFO`
- Portal-specific configs:
  - `MRF_PISOS_BASE_URL=...`
  - `MRF_SCRAPE_MAX_PAGES=...`

ConfigMaps hold non-sensitive defaults; Secrets hold credentials.

## Kubernetes objects (what you'll deploy)

### 1) API Deployment
- 1 replica
- Service: ClusterIP (internal, accessed via dashboard Nginx reverse proxy)

Suggested resources (Pi 5 friendly):
- requests: `cpu: 50m`, `memory: 128Mi`
- limits: `cpu: 300m`, `memory: 512Mi`

### 2) Dashboard Deployment
- Nginx serving static build + reverse proxy `/api/*` → backend ClusterIP
- 1 replica
- Service: LoadBalancer (MetalLB, IP: 192.168.79.42)

Resources:
- requests: `cpu: 20m`, `memory: 64Mi`
- limits: `cpu: 150m`, `memory: 256Mi`

### 3) Scraper CronJobs
One CronJob per portal.

Defaults:
- `concurrencyPolicy: Forbid` (don't overlap runs)
- `startingDeadlineSeconds: 600`
- `backoffLimit: 1` (fail fast)

Resources per scraper job:
- requests: `cpu: 100m`, `memory: 256Mi`
- limits: `cpu: 500m`, `memory: 768Mi`

If you introduce Playwright later, bump memory to ~1-1.5Gi for those jobs.

### 4) Optional PVC
Not strictly needed if you avoid large raw payload storage.
If you want debug HTML retention:
- PVC 1-2Gi `local-path` for `/data/debug` with a cleanup policy.

## ArgoCD Application manifest (example)

ArgoCD app points to repo path `k8s/apps/madrid-rental-finder/overlays/homelab`.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: madrid-rental-finder
  namespace: argocd
spec:
  project: data-services
  source:
    repoURL: https://github.com/Damianjsp/madrid-rental-finder.git
    targetRevision: main
    path: k8s/apps/madrid-rental-finder/overlays/homelab
  destination:
    server: https://kubernetes.default.svc
    namespace: madrid-rental-finder
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

## CI/CD (GitHub Actions)

Goal: build multi-arch images, push to ACR, ArgoCD auto-syncs.

### Required GitHub secrets
- `ACR_LOGIN_SERVER` = `dahomelab.azurecr.io`
- `ACR_USERNAME`
- `ACR_PASSWORD`

### Pipeline outline
1. On push to `main`:
   - build & push `api` image (linux/arm64, optionally amd64 too)
   - build & push `dashboard` image
   - (optional) update a kustomize image tag in repo and commit (or use `:sha` tags directly via ArgoCD Image Updater)

Two approaches:

#### A) GitOps-pure (recommended): ArgoCD Image Updater
- Install/configure ArgoCD Image Updater (if you already have it).
- Workloads reference image with a "track" tag (e.g. `main`).
- Image Updater updates manifests to new sha tags.

#### B) Simple and explicit: commit tag bumps
- CI runs `kustomize edit set image ...` and commits updated overlay.
- ArgoCD syncs because repo changed.

Given it's a personal tool, B is totally fine.

## Networking
- **No ingress/Traefik** — LAN-only access.
- Dashboard exposed via MetalLB LoadBalancer at `192.168.79.42:80`.
- Nginx in the dashboard container proxies `/api/*` to the backend ClusterIP.
- Single IP, single port. Access: `http://192.168.79.42`.

## Observability
Minimum:
- API `/healthz` and `/metrics`.
- CronJob logs to stdout.

Optional later:
- Grafana dashboard reading Prometheus/VictoriaMetrics.

## Security posture (reasonable for homelab)
- LAN-only (no public exposure). MetalLB IP not routable from internet.
- API is read-only. No auth needed for a single-user LAN tool.
