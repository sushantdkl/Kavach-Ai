# Observability design

Install with scripts/monitoring.ps1 after the testbed gate passes. Prometheus
discovers and scrapes individual payment pods (never the load-balanced Service)
every 2 seconds. It scrapes kubelet cAdvisor via the authenticated Kubernetes
API proxy for CPU counters and working-set memory. CPU source resolution is
limited by kubelet housekeeping; a 2s scrape does not imply 2s independent CPU
observations. Retain source timestamps and account for this in later analysis.

The first live check proved kubelet samples could be 14 seconds old, with empty
30-second CPU windows. Primary research CPU/memory now use the API container's
own cgroup v2 counters, read on every scrape. CPU usage_usec is converted to
seconds; working set is memory.current minus memory.stat inactive_file, clamped
at zero. A read timestamp is exposed. Unsupported cgroup hosts emit no resource
samples and fail collector validation. Native cAdvisor remains available as a
cross-check, and metrics-server/HPA sampling remains unchanged. See D006.

metrics-server v0.8.1 is vendored unchanged with a Kustomize patch adding
--kubelet-insecure-tls for kind's local kubelet certificates only. This exception
is limited to the disposable testbed. Source:
https://github.com/kubernetes-sigs/metrics-server/releases/tag/v0.8.1

Prometheus needs node proxy read access for cAdvisor and namespace pod discovery;
the API pod itself has no Kubernetes token. Grafana is ClusterIP-only with an
anonymous Viewer and a provisioned real Prometheus datasource. Host access uses
explicit loopback port-forwards. Monitoring storage is ephemeral; export each
run to immutable host files before restarting monitoring or removing the cluster.

The collector combines timestamped Prometheus samples with explicit Kubernetes
Deployment/pod/event snapshots. Required streams must be present and finite.
Missing data is not zero. Latency is undefined during a truly idle interval;
validate it conditionally on observed traffic and retain the null.

Application RPS is completed throughput, not offered demand. The later Locust
pipeline must export offered and admitted load as separate fields and expose
generator lag/drops; forecasting saturated completion rate alone is biased.

Scaling decisions/forecasts are null until their later phase is implemented.
OFF means no Kavach controller. Static runs may have zero scaling events; an
empty successful event snapshot is valid, a failed API read is not.

References:
- https://prometheus.io/docs/prometheus/latest/configuration/configuration/
- https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/
