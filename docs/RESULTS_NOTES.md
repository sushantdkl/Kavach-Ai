# Results and evidence ledger

No comparative experiments or ML results exist yet. No claim of improvement
over HPA is supported. Environment observations are in ENVIRONMENT.md.

Development smoke runs are engineering checks, not final research observations.
Gate evidence and failures will be saved under docs/evidence/; experimental raw
data belongs under experiments/raw/<unique_run_id>/ and is never overwritten.

## Phase 1 testbed gate — passed 2026-09-06

- 25 automated API/target-safety/manifest tests passed. Two third-party test-client
  deprecation warnings are recorded; lint passed after import formatting fixes.
- Docker image built with pinned Python base digest and hashed dependencies.
- kind-kavach-lab Kubernetes v1.34.0 node Ready; payment pod ready, zero restarts.
- Smoke 20260906T090923Z-f71dab03: 299 requests over 30 seconds at a 10 RPS
  ceiling, zero HTTP errors. Client mean 10 ms, p95 16 ms. Windows timer precision
  and kubectl port-forward affect these measurements. This is not calibration.
- Evidence: docs/evidence/phase1-*.{json,log} and the uniquely named smoke folder.
- Smoke metadata truthfully records a dirty documentation/evidence working tree;
  API source corresponds to commit 181e20a. Future research runs must use a
  clean experiment source tree and record cluster image IDs in run metadata.
## Phase 2 observability gate — passed 2026-09-06

- Prometheus application and cAdvisor targets healthy; metrics-server returns
  pod CPU/memory; Grafana ready with provisioned datasource.
- First unit test run: one missing-duration validation path raised TypeError;
  fixed the null handling and retained the failure log. All 48 tests now pass.
- First observation dc72d90d INVALID: cached kubelet CPU/memory timestamps too
  old and CPU windows sometimes empty. Fixed at source with fresh own-cgroup
  counters (D006), not by widening the freshness acceptance threshold.
- Observation 3f4ee284 INVALID: no initialized business counters after replacing
  the pod; the old port-forward was stale. Related smoke ebc7c06e also INVALID.
- Observation 28b279b0 PASS: 15/15 samples over 30s at 2s cadence, real traffic,
  latency, CPU/memory, replicas, restarts, pod snapshots and event stream complete.
  Parquet readback confirmed 15 rows. Every invalid artifact is retained.
- All observations are engineering-only and explicitly research-ineligible;
  Locust offered-load data and comparative baseline evidence are still pending.
