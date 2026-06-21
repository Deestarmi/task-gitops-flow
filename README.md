# task-gitops-flow

A hands-on practice project for learning GitOps on Kubernetes — built and debugged end-to-end on **Azure AKS** using the **KodeKloud Azure Playground// Free trial Azure **.

## What this project demonstrates

A complete GitOps pipeline where a Git commit is the only trigger needed to deploy to a Kubernetes cluster — no manual `kubectl apply`, no manual `helm install` once set up.

```
git push
   │
   ▼
GitHub Actions  →  builds Docker image, scans with Trivy, pushes to Docker Hub
   │
   ▼
Updates gitops/values-dev.yaml with the new image tag, commits back to the repo
   │
   ▼
Argo CD (running inside AKS)  →  detects the Git change automatically
   │
   ▼
Runs `helm upgrade` on the cluster  →  new pod replaces the old one
```

## Tools used

| Tool | Purpose |
|---|---|
| Git / GitHub | Source control, triggers the pipeline |
| GitHub Actions | CI — builds, scans, and pushes the Docker image |
| Docker | Packages the app into a container image |
| Trivy | Scans the image for known vulnerabilities before it ships |
| Docker Hub | Stores the built image |
| Helm | Templates the Kubernetes manifests for one or more environments |
| Argo CD | Watches Git and keeps the cluster in sync automatically (GitOps) |
| Azure AKS | Runs the actual Kubernetes cluster (via KodeKloud Playground) |

## Project structure

```
task-gitops-flow/
├── app.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── helm/
│   └── task-gitops-flow/
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
│           └── deployment.yaml      (Deployment + Service)
├── gitops/
│   ├── values-dev.yaml              (dev environment overrides)
│   └── argocd-app.yaml              (tells Argo CD what to watch and where to deploy)
└── .github/
    └── workflows/
        └── ci.yml                   (build → scan → push → update GitOps values)
```

## How it was set up on AKS (KodeKloud Playground)

1. Created the AKS cluster within the playground's resource group, using the allowed node size and node count limits.
2. Connected `kubectl` to the cluster via `az aks get-credentials`.
3. Installed Argo CD inside the cluster with Helm, in its own `argocd` namespace.
4. Retrieved the Argo CD admin password from the auto-generated Kubernetes secret and logged into the UI through a `kubectl port-forward` tunnel.
5. Pointed `gitops/argocd-app.yaml` at this GitHub repo, with the Helm chart path and the dev values file path set relative to the repo root.
6. Applied that file with `kubectl apply` — this registered the app inside Argo CD and triggered the first sync.
7. Verified the Deployment and Service landed correctly in the `dev` namespace.

## Key lessons learned while debugging this (real issues hit and fixed)

- **Helm `valueFiles` paths in an Argo CD Application are relative to the chart's `path`, not the repo root.** Got this wrong twice before landing on the correct `../../gitops/values-dev.yaml`.
- **A misplaced `templates/` folder produces zero Helm output with no error.** If `templates/` isn't a direct child of the folder containing `Chart.yaml`, Helm silently renders nothing — Argo CD then reports the app as "Healthy" simply because there's nothing unhealthy to report.
- **YAML indentation under `template.spec` is easy to get wrong.** A `spec:` block indented at the wrong level gets attached to the Deployment instead of the pod template, producing `spec.template.spec.containers: Required value`.
- **Hardcoded resource names cause drift between syncs.** Switched to `{{ .Release.Name }}` throughout the chart so the Deployment, Service, and pod labels always stay consistent with whatever Argo CD names the release.
- **Changing a Service's `type` field (ClusterIP → LoadBalancer) is not always a safe in-place patch.** When Argo CD's auto-heal tries to patch this kind of change, it can collide with an in-progress operation. Deleting the old Service and letting Argo CD recreate it fresh resolved this cleanly.
- **For real internal testing, `kubectl port-forward` is safer and cheaper than spinning up a `LoadBalancer` per service.** Reserved `LoadBalancer` (or a shared Ingress) for genuinely exposing something externally on purpose.

## Useful commands

```bash
# Connect to the cluster
az aks get-credentials --resource-group <RG> --name <AKS_NAME>

# Check Argo CD's view of the app
kubectl get application task-gitops-flow-dev -n argocd

# Check what's actually running, ground truth
kubectl get all -n dev

# Render the Helm chart locally without deploying (for debugging)
cd helm/task-gitops-flow
helm template task-gitops-flow-dev . --namespace dev --values ../../gitops/values-dev.yaml

# Open the Argo CD UI
kubectl port-forward svc/argocd-server -n argocd 8080:443 // kubectl patch application task-gitops-flow-dev -n argocd --type merge -p '{"operation":{"sync":{"revision":"HEAD"}}}'
```

## Status

Working end-to-end: a `git push` triggers a build, a security scan, a Docker Hub push, an automatic GitOps update, and an automatic Argo CD sync to the `dev` namespace on AKS.