# Deterministic synthetic workload replay

Each configuration freezes seed, duration, stage schedule, per-stage pattern
labels, request mix and max_rps. compile_trace creates the offered-request trace
before the experiment. Strategy changes never change the trace. The runner and
load pod independently hash it and require equality.

The Locust container uses one dispatcher with bounded request greenlets. This
is an open offered-load schedule rather than a user-count/closed-loop schedule.
It records every offer, dispatch delay, drop, completion and latency. More than
100ms dispatch lag or 200 concurrent requests causes a recorded generator drop
and invalidates the run. No catch-up bursts are emitted. Ceiling: at most 400
requests/s; current fixture scenarios are development values, not calibrated
final comparisons. HTTP redirects/proxies are disabled.

The runner verifies the local kind control plane and payment Service identity;
the load pod verifies Service DNS against its assigned ClusterIP and probes the
synthetic fixture before sending load. Only the verified literal Service IP is
used for HTTP. Connections close after each request so Kubernetes can distribute
traffic across replicas consistently. This connection model must be held fixed
and described in thesis limitations.

Session tokens and portable receipts are generated offline from documented
synthetic fixture values, avoiding strategy-dependent setup requests. No real
credentials or actual payments exist. Application-side errors remain outcomes;
generator drops invalidate experimental comparability.

Build/load:

```powershell
docker build -f workload/Dockerfile -t kavach-workload:dev .
./.tools/kind.exe load docker-image kavach-workload:dev --name kavach-lab
uv run python -m experiments.run experiments/configs/smoke.yaml
```

Prometheus's loopback port-forward must be running. Commit tracked source
changes first. Output defaults to experiments/raw/<unique-id>. Successful
artifact export permits removal of that run's load pod/config only; raw output
is retained, including all invalid runs. Partial preflight failures may contain
only diagnostic metadata/validation. Check checksums.json before later analysis.

HPA_CANDIDATE is explicitly uncalibrated. The runner deliberately does not expose
HPA_TUNED or KAVACH before their acceptance evidence and configuration exist.
