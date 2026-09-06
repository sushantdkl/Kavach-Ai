# Kavach AI

University research artefact by Sushant Dhakal (240005): AI-powered predictive
autoscaling for resilient synthetic payment APIs under flash-crowd and
attack-like traffic. Workloads are confined to an isolated local testbed.

Implementation is progressing through the evidence gates in
[docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md). No comparative
results exist yet. Read [the architecture](docs/ARCHITECTURE.md),
[decisions](docs/DECISIONS.md), [environment](docs/ENVIRONMENT.md) and
[experiment protocol](docs/EXPERIMENT_PROTOCOL.md).

The master prompt defines the required order: working API/Kubernetes,
observability, reproducible Static/tuned-HPA baselines, datasets, ML, shadow,
active controller, evaluation, then dashboard. Later phases remain pending
until the preceding acceptance evidence exists.

## Development setup

Install Python 3.12, uv, Docker Desktop (Linux containers), kubectl and kind.
Dependencies and hashes are committed in uv.lock and requirements-api.lock.
On Windows, place the kind binary at .tools/kind.exe. The tested version is
v0.33.0; verify its release SHA-256 before execution.

```powershell
./scripts/bootstrap.ps1
./scripts/testbed.ps1 create
./scripts/testbed.ps1 build
./scripts/testbed.ps1 deploy
kubectl --kubeconfig infrastructure/kubeconfig --context kind-kavach-lab -n kavach-lab port-forward --address 127.0.0.1 service/payment-api 8000:8000
# In a second terminal:
uv run python scripts/smoke.py --target http://127.0.0.1:8000 --rps 10 --duration 30
```

For API-only development: `uv run uvicorn app.main:app --app-dir payment-api
--host 127.0.0.1 --port 8000`. API docs are at http://127.0.0.1:8000/docs.
Synthetic fixture login: `synthetic-user-1` / `synthetic-only`. There is no real
authentication or money transfer. Confirmation does not persist balance changes.
Smoke output is uniquely named and is not research comparison data.

Do not reuse unrelated clusters. Every project kubectl command uses the local
kubeconfig and `kind-kavach-lab` context. No public Service or ingress is created.
