# Implementation plan and gate ledger

Follow ASTRA_MASTER_PROMPT.md when it conflicts with the specification. Each gate
needs measured evidence and a commit. Never infer gate success from file presence.

| Phase | Work and acceptance evidence | Status |
|---|---|---|
| 0 Research freeze | Preserve input docs, RQ/H, source audit, ethics, decisions | In progress |
| 1 Testbed | Tested synthetic API, reproducible image, isolated Kubernetes, fixed-load smoke | In progress |
| 2 Observability | Prometheus, metrics-server, Grafana, complete synchronized streams | Pending phase 1 |
| 3 Baselines | Seeded trace replay, capacity/readiness calibration, repeated Static/tuned HPA runs | Pending phase 2 |
| 4 Dataset | Immutable run artifacts, coverage validation, run-level chronological partitions | Pending phase 3 |
| 5 Forecast | Last-value/EWMA/RF/XGB at 5/10/15/30s; unseen-run evaluation | Pending phase 4 |
| 6 Pattern | Engineered features, classifier, per-class reports and failures | Pending phase 5 |
| 7 Shadow | Complete decisions, valid bounds, freshness and oscillation checks | Pending phase 6 |
| 8 Active | Guarded actuation, fallback, readiness outcome evidence | Pending phase 7 |
| 9 Evaluation | Frozen repeated matrix, blocked strategy order, statistics and plots | Pending phase 8 |
| 10 UI | Real experiment API and dashboard; Figma using implemented fields | Pending phase 9 |
| 11 Thesis | Methods/results/limitations/reproduction appendix | Pending phase 10 |

Current sequence: establish version control and method documents; build/test API;
start the existing Docker runtime; create an explicitly named disposable kind
cluster; build/load image; deploy and run a bounded loopback smoke. Do not start
ML or dashboard before earlier gates pass. If the host blocks Kubernetes, retain
all diagnostics and complete only work belonging to the current phase.
