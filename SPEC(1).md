# Kavach AI — Implementation and Experiment Specification

**Status:** Research implementation specification  
**Owner:** Sushant Dhakal — 240005  
**Project:** Kavach AI  
**Primary environment:** Local, isolated Kubernetes testbed  
**Research style:** Design Science Research + controlled repeated experimentation

---

# 0. Non-negotiable project rules

1. Do not target any real payment system.
2. Do not use real financial/customer data.
3. Do not send attack-like traffic outside the isolated lab environment.
4. Do not claim production readiness.
5. Do not optimize results by weakening baselines.
6. Do not let the predictive model directly control replicas without safety logic.
7. Every scaling decision must be logged and explainable.
8. Every experiment must be reproducible from configuration + seed + git commit.
9. Research metrics take priority over dashboard polish.
10. Any LLM/SLM component must not be in the safety-critical actuation path.

---

# 1. Deliverables

## D1 — Reproducible payment-API testbed
A synthetic API with enough realistic work to respond to CPU/load changes.

Suggested endpoints:
- POST /auth/login
- GET /wallet/balance
- POST /payments/initiate
- POST /payments/confirm
- GET /transactions/{id}
- GET /health
- GET /metrics

No real payments occur.

## D2 — Kubernetes deployment
- Deployment
- Service
- ConfigMap
- Secret only for synthetic/local values
- resource requests/limits
- liveness/readiness/startup probes
- fixed replica manifest
- HPA manifest
- optional KEDA manifests

## D3 — Observability
- Prometheus
- Grafana
- metrics-server
- application Prometheus metrics
- experiment event logger

## D4 — Workload generator
Locust preferred.

Config-driven scenarios:
- steady
- ramp
- flash
- repeated burst
- oscillatory
- sustained overload
- hybrid
- recovery

Each scenario:
- deterministic seed
- max RPS ceiling
- exact duration
- exact stage schedule
- synthetic request mix

## D5 — Dataset pipeline
Raw observations stored at a fixed interval, recommended 1s or 2s.

Fields:
- run_id
- timestamp
- strategy
- scenario
- random_seed
- current_rps
- success_rps
- error_rps
- latency_p50_ms
- latency_p95_ms
- latency_p99_ms
- cpu_usage_cores
- cpu_utilization_pct
- memory_bytes
- ready_replicas
- desired_replicas
- pending_replicas
- pod_start_events
- restart_count
- current_slo_violation
- scaling_event
- scaling_reason
- forecast_rps_horizon
- forecast_error
- burst_score
- burst_class
- controller_mode
- git_commit

Store raw immutable data separately from processed features.

## D6 — Forecasting pipeline
Models:
- naive last value
- moving average / EWMA baseline
- Random Forest
- XGBoost
- optional compact temporal model only if justified

Primary target:
- RPS H seconds into the future

Candidate horizons:
- 5 s
- 10 s
- 15 s
- 30 s

Choose based on measured pod readiness time. The best horizon is not arbitrary: it should roughly match the time needed for a scaling decision to become useful.

## D7 — Pattern/burst intelligence
Required non-generative classifier.

Classes:
- steady
- ramp
- flash
- oscillatory
- sustained overload
- recovery

Candidate features:
- rps delta
- rolling slope
- rolling std
- coefficient of variation
- autocorrelation
- peak-to-mean ratio
- CPU slope
- latency slope
- error slope
- replica state

Model:
- XGBoost/RandomForest classifier initially
- optional small transformer classifier as a research extension

## D8 — Kavach controller
Modes:
- OFF
- SHADOW
- ACTIVE

Shadow:
- calculates desired replicas
- never patches Kubernetes
- logs recommendation

Active:
- applies guarded recommendations

Decision flow:
1. collect fresh metrics
2. reject stale/invalid metrics
3. forecast demand
4. classify current workload pattern
5. estimate safe replica requirement
6. apply burst/safety policy
7. apply cooldown/stabilization
8. clamp min/max
9. log decision
10. patch scale subresource
11. monitor readiness result
12. feed result into evaluation logs

## D9 — Experiment runner
One command should run a configured experiment and produce:
- raw metrics CSV/Parquet
- Locust stats
- Kubernetes events
- controller decisions
- metadata JSON
- final summary JSON

## D10 — Research dashboard
Dashboard is not the controller.

Pages:
1. Experiment overview
2. Live workload
3. Forecast vs actual
4. Scaling decisions
5. SLO/latency
6. Resource usage
7. Strategy comparison
8. Model evaluation
9. Experiment history
10. Decision explanation

---

# 2. Recommended technology stack

## API
Python FastAPI

Reason:
- easiest integration with Prometheus and ML code
- simple synthetic CPU/IO workloads
- fewer cross-language experiment complications

## Database
PostgreSQL optional for synthetic transaction state.

For experiment data:
- Parquet/CSV as canonical research output
- optional PostgreSQL copy for dashboard queries

## Load
Locust

## Containers
Docker

## Kubernetes
Start with Minikube or kind.

Minikube is easier for a first thesis demonstration.
kind is excellent for reproducible disposable clusters.
The implementation may support both later.

## Monitoring
- Prometheus
- Grafana
- metrics-server

## ML
- pandas
- numpy
- scikit-learn
- xgboost
- scipy
- statsmodels if needed
- shap optional for feature explanation

## Controller
Python service using official Kubernetes Python client.

## UI
Next.js + TypeScript + Tailwind/shadcn if desired.
Do not start UI until the experiment pipeline works.

---

# 3. Repository structure

kavach-ai/
├─ README.md
├─ docs/
│  ├─ RESEARCH_BASELINE.md
│  ├─ SPEC.md
│  ├─ ETHICS.md
│  ├─ EXPERIMENT_PROTOCOL.md
│  ├─ ARCHITECTURE.md
│  └─ DECISIONS.md
├─ payment-api/
│  ├─ app/
│  ├─ tests/
│  ├─ Dockerfile
│  └─ pyproject.toml
├─ workload/
│  ├─ locustfile.py
│  ├─ scenarios/
│  └─ README.md
├─ infrastructure/
│  ├─ k8s/
│  │  ├─ base/
│  │  ├─ static/
│  │  ├─ hpa/
│  │  ├─ keda/
│  │  └─ monitoring/
│  └─ scripts/
├─ collector/
│  ├─ collectors/
│  ├─ schemas/
│  └─ tests/
├─ ml/
│  ├─ datasets/
│  ├─ features/
│  ├─ forecasting/
│  ├─ patterns/
│  ├─ evaluation/
│  └─ artifacts/
├─ controller/
│  ├─ forecasting.py
│  ├─ pattern.py
│  ├─ capacity.py
│  ├─ safety.py
│  ├─ controller.py
│  ├─ logger.py
│  └─ tests/
├─ experiments/
│  ├─ configs/
│  ├─ runner/
│  ├─ raw/
│  ├─ processed/
│  └─ reports/
├─ dashboard/
├─ notebooks/
├─ scripts/
├─ Makefile
└─ .github/workflows/

---

# 4. Synthetic payment API design

The API needs controlled reproducible latency/resource behavior.

Each request can contain:
- validation
- synthetic token verification
- deterministic hashing
- small DB operation
- configurable CPU-work unit
- configurable I/O delay

Environment knobs:
- KAVACH_CPU_WORK_FACTOR
- KAVACH_IO_DELAY_MS
- KAVACH_ERROR_INJECTION_RATE (default 0)
- KAVACH_DB_ENABLED

Do not use random hidden behavior during controlled tests unless the random seed is recorded.

---

# 5. SLO definition

Define before experiments.

Initial candidate SLO:
- p95 < 300 ms
- error rate < 1%

These are provisional and must be calibrated from the actual local testbed.

Procedure:
1. benchmark one pod
2. find saturation curve
3. determine sustainable per-pod RPS
4. choose SLO where the service is useful but load can realistically cause violation
5. freeze SLO before final comparison

Do not pick an SLO after seeing which strategy wins.

---

# 6. Capacity model

Do not let XGBoost output replica count directly.

After calibration:

safe_capacity_per_pod = empirically measured RPS at chosen utilization/SLO margin

base_required =
ceil(predicted_rps / safe_capacity_per_pod)

Then adjust using:
- p95 pressure
- error pressure
- burst class
- current ready replicas
- pod startup delay

Keep the mapping deterministic and documented.

---

# 7. Kavach controller policy v1

Inputs:
- current_rps
- predicted_rps
- cpu
- p95
- error_rate
- ready_replicas
- burst_class
- burst_score
- prediction_error_health

### Scale-up
If:
- forecast indicates capacity deficit
AND forecast quality is healthy

then pre-scale.

If:
- actual p95/error/CPU indicates immediate overload

then emergency reactive scale-up even if forecast fails.

### Oscillatory/attack-like pattern
Do not blindly block scaling.
That could intentionally make availability worse.

Instead:
- use bounded scale-up
- prefer smaller increments
- enforce max replica ceiling
- raise anomaly flag
- shorten decision interval if safe
- preserve minimum availability capacity
- log `attack_cost_guard_active=true`

### Scale-down
Only if:
- observed demand has remained below threshold for a stable window
- no active burst
- p95 healthy
- forecast not rising
- minimum cooldown elapsed

Scale-down should be slower than scale-up.

---

# 8. Prediction health and fallback

Maintain rolling forecast error.

States:
- HEALTHY
- DEGRADED
- UNTRUSTED

If UNTRUSTED:
- disable predictive pre-scaling
- fall back to reactive controller
- continue logging forecasts in shadow
- recover only after error returns below threshold for N windows

This is a simple drift/uncertainty safeguard without turning the thesis into a full concept-drift project.

---

# 9. LLM / model architecture decision

## Core controller
No generative LLM.

## "Our own" intelligence
We train:
- forecast model(s) on our generated traces
- pattern classifier on our generated traces

## Optional custom transformer
If required by supervisor:
- build a compact time-series Transformer encoder from scratch
- numerical windows in
- workload pattern logits / future load out
- compare against RF/XGBoost
- do not call it an LLM

## Optional local language model
Only for explanation/pattern-advisor experiments:
- offline/local open-weight small model
- structured JSON input
- schema-constrained JSON output
- no Kubernetes write permission
- never part of mandatory controller success path

---

# 10. Baseline configurations

## Static
- fixed N replicas
- N selected through calibration
- no autoscaler

## HPA
Use autoscaling/v2.
At minimum:
- CPU metric
- exact target documented
- exact behavior/stabilization documented
- exact min/max same as Kavach

Create:
- HPA-default baseline
- HPA-tuned baseline if time permits

## KEDA optional
Prometheus RPS query scaler.
Use same min/max.

This prevents the thesis from claiming novelty over an intentionally primitive reactive baseline.

---

# 11. Experiment matrix

Core final matrix:

Strategies:
- STATIC
- HPA_TUNED
- KAVACH

Scenarios:
- STEADY
- RAMP
- FLASH
- REPEATED_BURST
- OSCILLATORY
- SUSTAINED_OVERLOAD
- HYBRID
- RECOVERY

Repetitions:
- minimum 5
- preferred 10

3 × 8 × 10 = 240 final runs

If this is too slow:
- use 5 repetitions during development
- reserve 10 for the final selected scenario set

---

# 12. Fairness controls

Before every run:
- verify image digest
- verify git commit
- reset strategy manifest
- reset/label cluster state
- clear prior experiment labels
- wait for stable ready replicas
- verify Prometheus scrape
- verify load generator time synchronization
- record environment information

During:
- never manually intervene
- collect all metrics at fixed cadence

After:
- stop workload
- export data
- wait/reset
- validate output completeness
- mark run PASS/INVALID

Invalid runs are not deleted. They are recorded with reason.

---

# 13. Statistical analysis

For each scenario:
- mean
- median
- standard deviation
- 95% confidence interval

Compare strategies on:
- p95 latency
- error rate
- SLO violation duration
- resource index
- effective scaling delay

Use:
- distribution/normality checks
- ANOVA only when assumptions are reasonable
- otherwise Kruskal-Wallis / paired non-parametric methods as appropriate
- effect sizes, not p-values alone

Randomization:
- run ordering should be randomized or blocked to reduce time/environment bias.

---

# 14. Research dashboard design brief

Visual identity:
- serious observability/AIOps system
- not a crypto dashboard
- not sci-fi neon
- dark/light capable
- readable charts
- exact units
- no fake metrics

Primary live screen:
- current RPS
- predicted RPS + horizon
- actual replicas
- recommended replicas
- p95 latency
- error rate
- current pattern
- controller health
- current scaling reason

Central chart:
Actual RPS vs Predicted RPS

Aligned chart:
Ready/Desired Replicas over time

Aligned chart:
p95 latency with SLO line

Decision timeline:
- timestamp
- decision
- trigger
- model confidence/error
- safety guard
- result

Figma should represent the **real implemented data model**, not invent features.

---

# 15. Development phases and gates

## Phase 0 — Research freeze
Deliver:
- spec
- source matrix
- exact RQ/H
- ethics boundary
Gate:
- no architecture contradictions

## Phase 1 — Testbed
Deliver:
- API
- Docker
- Kubernetes deployment
- synthetic data
Gate:
- stable API under fixed load

## Phase 2 — Observability
Deliver:
- Prometheus
- metrics-server
- Grafana
- app metrics
Gate:
- complete synchronized time series

## Phase 3 — Baselines
Deliver:
- Static
- HPA tuned
- workload scenarios
Gate:
- repeatable baseline results

## Phase 4 — Dataset
Deliver:
- repeated runs
- raw schema
- feature pipeline
Gate:
- no leakage, enough variation

## Phase 5 — Forecasting
Deliver:
- last-value
- EWMA
- RF
- XGB
- horizon selection
Gate:
- time-ordered evaluation complete

## Phase 6 — Pattern intelligence
Deliver:
- pattern labels
- classifier
- burst score
Gate:
- confusion matrix + failure cases

## Phase 7 — Shadow controller
Deliver:
- recommendations only
- decision logs
Gate:
- no unsafe/impossible recommendations

## Phase 8 — Active controller
Deliver:
- guarded Kubernetes scaling
- fallback
Gate:
- survives test scenarios

## Phase 9 — Final experiments
Deliver:
- complete matrix
- statistics
- plots
Gate:
- reproducible findings

## Phase 10 — Dashboard/Figma
Deliver:
- implemented research dashboard
- Figma aligned with real UI
Gate:
- no invented data/claims

## Phase 11 — Thesis
Deliver:
- methods
- results
- limitations
- reproducibility appendix

---

# 16. Acceptance criteria

The project is successful even if H2 is not supported.

Scientific success means:
- reproducible system
- valid comparison
- complete data
- transparent negative/positive findings
- clear limitations

Technical minimum:
- fixed API testbed
- Kubernetes
- Prometheus
- load generation
- static baseline
- HPA baseline
- trained forecast model
- burst classifier
- shadow + active Kavach controller
- final repeated evaluation

---

# 17. Out of scope

- real banking integration
- PCI-DSS production certification
- real DDoS mitigation
- public attack testing
- multi-region Kubernetes
- service mesh research
- VPA optimization
- cluster/node autoscaling research
- full reinforcement learning controller
- foundation LLM training
- production cloud cost claims
- multi-cloud deployment

Any of these may be listed as future work.
