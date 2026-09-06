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
