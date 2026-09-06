# Decision record

## D001 — Input precedence and baselines
Decision: master prompt controls sequencing; tuned HPA is mandatory. Preserve
original root documents, copy supplied baseline and SPEC(1).md to the canonical
docs paths. Alternative: treat spec's 'tuned if time permits' as optional.
Reason: explicit master prompt makes tuned HPA mandatory. Research consequence:
no artificially weak reactive comparator. The source documents themselves are
requirements and hypotheses, not verified experimental findings.

## D002 — Isolated local kind cluster
Decision: use a named kind cluster with a project-local kubeconfig and explicit
context. Alternative: enable Docker Desktop's global Kubernetes or Minikube.
Reason: avoid changing existing global contexts; support disposable reproduction.
Consequence: one physical machine cannot represent multi-node cloud performance.
Docker startup must succeed before cluster acceptance.

## D003 — Synthetic stateless payment fixture
Decision: deterministic signed transaction receipts, synthetic user fixture and
idempotent confirmation, no database or actual transfer. Alternative: mutable
per-pod dict or PostgreSQL. Reason: per-pod state gives false 404s when requests
land on another replica; a database adds a second scaling bottleneck.
Consequence: conclusions concern compute/IO API behavior, not payment durability,
balance mutation, fraud prevention or database-bound payment throughput.

## D004 — One process per container
Decision: one Uvicorn worker, bounded configurable deterministic CPU work and IO
delay. Alternative: multiple workers per pod. Reason: isolate horizontal replica
effects and avoid process-local Prometheus aggregation ambiguity. Consequence:
capacity is calibrated for this exact process topology and resource envelope.
Reference: https://fastapi.tiangolo.com/deployment/docker/

## D005 — Phase gates are evidence requirements
Decision: no forecasting/controller/UI implementation until prerequisite gates
pass. Alternative: scaffold the entire stack before running it. Reason: master
prompt forbids jumping forward. Consequence: an environment blocker may leave
later deliverables pending; no simulated results may stand in for cluster data.
## D006 — Fresh cgroup counters for the research collector
Decision: expose the container's own cgroup v2 CPU counter and memory working set
at each /metrics scrape; retain kubelet cAdvisor and metrics-server for independent
inspection/HPA. Alternative: relax freshness to accept 15-second cached kubelet
samples, or alter kubelet behavior. Reason: observed first live collector run had
stale CPU/memory and empty rate windows. Kubernetes hardcodes dynamic cAdvisor
housekeeping up to 15 seconds. Consequence: short-interval collector CPU is based
on actual cgroup counters with explicit read timestamps; HPA's native metrics
timing is unchanged. Same API instrumentation applies to every strategy.
Source: https://github.com/kubernetes/kubernetes/blob/v1.34.0/pkg/kubelet/cadvisor/cadvisor_linux.go
