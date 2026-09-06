# Kavach AI architecture

Planned pipeline: deterministic Locust request trace → synthetic FastAPI service
in Kubernetes → Prometheus and Kubernetes telemetry → collector → immutable raw
run → processed temporal features → forecast and pattern models → deterministic
capacity/safety policy → shadow recommendations → guarded active scaling →
statistical comparison → research dashboard.

The API owns no real financial state. Transaction receipts are portable across
replicas. API metrics use route templates and status labels; health/metrics
traffic is excluded from business-demand metrics. The controller must operate
without any generative language model. ML predicts demand, not replica counts.

Current implementation scope is recorded in IMPLEMENTATION_PLAN.md. Planned
components in this document must not be represented as implemented or validated.
