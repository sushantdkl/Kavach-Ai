# Baseline calibration ledger

No HPA setting is called tuned until separate calibration data supports it.
Candidate manifest: infrastructure/k8s/hpa/candidate.yaml. CPU utilization target
60% of requested 250m, bounds 1–6 pods, up max(100%,4 pods)/15s, down one pod/30s
after 60s stabilization. Native cluster tolerance is used, no version-dependent
tolerance field is set. API resource request 250m/128Mi, limit 500m/256Mi applies
unchanged to every strategy. Candidate values may change only before final freeze.

## Engineering acceptance

- In-cluster smoke 20260906T093127Z-85049d0d passed: all 600 offers recorded,
  identical trace SHA-256, no generator drops, full metrics. Excluding declared
  20s warm-up leaves 400 requests, zero errors, client p95 9.15 ms.
- Prior smoke 051beeeb failed due to a Locust reserved-property collision; logs
  retained and the runtime bug fixed. Empty traffic was not reported as success.
- Five idle scale-1-to-2 trials: 3.765–3.969s decision-to-ready, mean 3.8464s,
  0.2s polling resolution. Raw pod timestamps retained in readiness-713fbe05.
  This is warm-image local readiness, not cold registry pull or cloud provisioning.

## Capacity protocol

The first exploration uses one pod, 30s warm-up, 60s steps at 20/40/80/120/180/240
RPS and 60s recovery. Exclude the first 10s of each step for the stage report.
This exploration locates the saturation region; repeat separate constant-rate
runs near the boundary before freezing capacity. HTTP errors and timeouts are
outcomes, not automatic invalidation; missing telemetry, runtime errors, missing
requests or generator drops do invalidate a run.

Initial 300ms p95 / 1% error SLO stays provisional. Select safe capacity with
headroom using valid calibration observations; do not tune against test traces.
Then compare HPA candidate settings with a predeclared validation objective
balancing SLO duration, client latency, errors, pod-seconds and oscillation.

Final experiments require at least five repeats per scenario/strategy, blocked
by trace seed, with order randomized inside blocks. A single successful smoke
or capacity sweep does not pass the baseline gate.
