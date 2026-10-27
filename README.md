# 🚦 CICD-Pipeline-Demo

**Small app. Serious pipeline.** ✨

The API is a few lines of Python serving driving scenarios. It's here so the pipeline has something to ship. The pipeline is the point: every change is linted, tested, containerised, published and deployed to Kubernetes without anyone touching a cluster.

---

## 🗺️ The pipeline

```
   Developer
      │  git push / open PR
      ▼
 ┌─────────┐     ┌─────────┐     ┌──────────┐
 │  TEST   │────►│  BUILD  │────►│  DEPLOY  │
 │ ruff    │     │ docker  │     │ bump tag │
 │ pytest  │     │ cache   │     │ in k8s/  │
 └─────────┘     └────┬────┘     └────┬─────┘
   every PR           │ main only     │ main only
                      ▼               ▼
               ┌────────────┐   ┌────────────┐
               │    GHCR    │   │  Git repo  │
               │ image:sha  │   │   k8s/     │
               └─────┬──────┘   └─────┬──────┘
                     │ pull           │ watch
                     ▼                ▼
               ┌──────────────────────────────┐
               │   Kubernetes   +   Argo CD   │
               │   scenario-api  x2 replicas  │
               └──────────────────────────────┘
```

CI builds the artifact and records the intent in Git. Argo CD makes it so. CI never holds the keys to the cluster. 🔐

---

## 🔁 How a change flows

1. **Open a PR.** A fresh, ephemeral runner checks out the code.
2. **Test.** Ruff lints and checks formatting, and pytest runs the tests. The cheapest checks run first.
3. **Build.** A multi-stage Docker image, built on cached layers. PRs build the image but don't publish it.
4. **Merge to main.** The image is pushed to GHCR, tagged with the commit SHA. Never `latest`.
5. **Deploy.** A bot commits the new tag to `k8s/kustomization.yml`.
6. **Roll out.** Argo CD sees the commit and performs a zero-downtime rolling update. 🚀

---

## 🧠 Design decisions

| Decision | Why |
|---|---|
| **Pull-based GitOps (Argo CD)** | No cluster credentials in CI. Every deploy is a commit, rollback is `git revert`, and manual drift gets reverted automatically. |
| **Lockfile enforced with `--locked`** | Same dependencies on a laptop, in CI and in production. Reproducible by default. |
| **Image tag = commit SHA** | Immutable, traceable artifacts. You always know exactly what's running. |
| **Multi-stage, slim, non-root image** | Build tools stay in the build stage. Less to ship, less to patch, less to exploit. |
| **Layer caching** (uv + GHA Docker cache) | Runners are disposable; build times don't have to be. ⚡ |
| **Pin everything** (actions by SHA, runner `ubuntu-24.04`) | Moving targets cause mystery breakages. Upgrades happen on purpose. |
| **Dependabot** | Pins without updates go stale. Weekly bumps, each one tested by the pipeline. |
| **Least-privilege tokens per job** | Read-only by default. Only `build` can push images, and only `deploy` can commit. |
| **Pre-commit hooks** | Fast feedback locally. CI remains the enforced gate. |

---

## 🗂️ Repo layout

```
app/main.py                 the API (/healthz, /scenarios)
tests/                      pytest tests
pyproject.toml, uv.lock     dependencies, pinned
Dockerfile                  multi-stage, slim, non-root
.github/workflows/ci.yml    test → build → deploy
.github/dependabot.yml      automated dependency updates
.pre-commit-config.yaml     local checks before every commit
k8s/                        Deployment, Service, Kustomize
argocd/application.yml      what Argo CD watches and where it deploys
```

---

## 🛠️ Run it yourself

There are three levels. Go as deep as you like.

### Prerequisites

| Tool | Needed for | Install (macOS) |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | Level 1 | `brew install uv` |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | Levels 2 and 3 | Download, then start it |
| [kind](https://kind.sigs.k8s.io/) | Level 3 | `brew install kind` |
| [kubectl](https://kubernetes.io/docs/tasks/tools/) | Level 3 | `brew install kubectl` |

```bash
git clone https://github.com/sianrachel/CICD-Pipeline-Demo.git
cd CICD-Pipeline-Demo
```

### 🐍 Level 1: Run the app

```bash
uv sync                                   # install from the lockfile
uv run pytest                             # run the tests
uv run uvicorn app.main:app --reload      # start the API
```

Open http://127.0.0.1:8000/healthz, http://127.0.0.1:8000/scenarios or the interactive docs at http://127.0.0.1:8000/docs.

Optional, if you're contributing: `uv run pre-commit install` enables the git hooks.

### 🐳 Level 2: Run it in Docker

**Build it yourself:**

```bash
docker build -t scenario-api .
docker run --rm -p 8000:8000 scenario-api
```

**Or pull the exact image CI published** (the tag currently deployed is in `k8s/kustomization.yml`):

```bash
TAG=$(grep newTag k8s/kustomization.yml | awk '{print $2}')
docker run --rm -p 8000:8000 ghcr.io/sianrachel/cicd-pipeline-demo:$TAG
```

Then open http://127.0.0.1:8000/healthz. Stop it with `Ctrl+C`.

Run `docker build` a second time and every layer comes back `CACHED`. That's the layer-caching design at work.

### ☸️ Level 3: The full GitOps setup (Kubernetes + Argo CD)

This runs a real Kubernetes cluster on your machine with Argo CD deploying the app from this repo.

**1. Create a local cluster**

```bash
kind create cluster --name argo-demo
```

**2. Install Argo CD** (pinned version)

```bash
kubectl create namespace argocd
kubectl apply -n argocd --server-side \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.6/manifests/install.yaml
kubectl -n argocd rollout status deploy/argocd-server --timeout=300s
```

**3. Point Argo CD at this repo**

```bash
kubectl apply -f argocd/application.yml
```

**4. Open the Argo CD UI**

```bash
# admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d; echo

# UI (leave this running)
kubectl -n argocd port-forward svc/argocd-server 8443:443
```

Go to **https://localhost:8443**, accept the self-signed certificate warning, and log in as `admin`. You'll see `scenario-api` synced and healthy: a Service, a Deployment and two pods. 💚

**5. Call the app in the cluster** (in a second terminal)

```bash
kubectl -n scenario-api port-forward svc/scenario-api 8080:80
```

Then open http://localhost:8080/healthz.

**6. See self-heal in action**

```bash
kubectl -n scenario-api scale deploy/scenario-api --replicas=5
```

Watch Argo CD put it straight back to 2. Git is the source of truth, and manual changes don't stick.

**7. Clean up**

```bash
kind delete cluster --name argo-demo
```

<details>
<summary>🍴 <b>Running your own fork</b></summary>

To have *your* pushes deploy to *your* cluster:

1. Fork the repo and enable Actions on the fork.
2. Under **Settings → Actions → General → Workflow permissions**, select **Read and write**, so the deploy job can commit.
3. In `argocd/application.yml`, change `repoURL` to your fork.
4. In `k8s/kustomization.yml`, change `newName` to `ghcr.io/<your-username>/<your-repo-name>` (lowercase).
5. Push to `main`, wait for the pipeline to go green, and make the published package public under **Packages → Package settings**.

</details>

<details>
<summary>🔒 <b>Using a private repo or private image</b></summary>

Argo CD needs credentials to read the repo, and the cluster needs credentials to pull the image. With the GitHub CLI:

```bash
gh auth refresh -s read:packages

# Argo CD → private repo
kubectl -n argocd create secret generic repo-cicd \
  --from-literal=type=git \
  --from-literal=url=https://github.com/<owner>/<repo>.git \
  --from-literal=username=<owner> \
  --from-literal=password="$(gh auth token)"
kubectl -n argocd label secret repo-cicd argocd.argoproj.io/secret-type=repository

# Cluster → private image (the deployment references this secret)
kubectl create namespace scenario-api
kubectl -n scenario-api create secret docker-registry ghcr-creds \
  --docker-server=ghcr.io \
  --docker-username=<owner> \
  --docker-password="$(gh auth token)"
```

Do this between steps 2 and 3. For anything beyond a local demo, use a dedicated read-only token or a GitHub App, managed by something like External Secrets.

</details>

---

## 🔭 What's next

- 🛡️ **Supply chain:** SBOMs (Syft), signed images (cosign) and vulnerability scanning (Trivy), with the cluster only admitting signed images.
- 🌍 **Environments:** dev, staging and prod overlays, with promotion to prod through a reviewed PR.
- 🏎️ **Scale:** autoscaling self-hosted runners on Kubernetes (Actions Runner Controller) and a shared remote build cache.
- 🧩 **Self-service:** reusable workflows, so a new service inherits this pipeline in a few lines of YAML.
- 🐤 **Progressive delivery:** Argo Rollouts canaries that roll back automatically when the metrics say no.
- 📊 **Observability:** build times, cache hit rates, flaky-test tracking and DORA metrics.

---

<sub>🐍 Python · ⚡ uv · 🐳 Docker · ⚙️ GitHub Actions · ☸️ Kubernetes · 🐙 Argo CD</sub>
