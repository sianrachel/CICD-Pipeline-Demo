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

## 🏃‍♀️ Run it locally

```bash
uv sync                                   # install from the lockfile
uv run pytest                             # run the tests
uv run uvicorn app.main:app --reload      # http://127.0.0.1:8000/healthz
docker build -t scenario-api .            # build the image
uv run pre-commit install                 # enable the git hooks
```

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

