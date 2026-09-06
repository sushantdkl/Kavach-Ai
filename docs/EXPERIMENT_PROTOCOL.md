# Experiment protocol (pre-calibration draft)

RQ1 and RQ2 and H1/H2 are frozen in RESEARCH_BASELINE.md sections 5–6. H1 tests
future-RPS forecasting against last-value; H2 tests the latency/reliability versus
resource/stability trade-off against calibrated static and tuned HPA. Negative
results are acceptable. No hypothesis has yet been tested.

Before comparative runs, measure one-pod saturation and readiness delay. Freeze
safe per-pod RPS, SLO, replica bounds and controller settings using calibration
and validation runs only. Candidate SLO p95 <300 ms and errors <1% is provisional.

Use identical image digest, pod resources, probes, workload trace/seed, sampling
interval and duration across strategies. Static N is calibrated. Tuned HPA uses
autoscaling/v2 with documented CPU target, stabilization, limits and policies.
Its tuning uses separate calibration data. Keep HPA absent during static and
active Kavach runs to avoid competing writers.

Scenarios: steady, ramp, flash, repeated burst, oscillatory, sustained overload,
hybrid, recovery. At least five repetitions per strategy/scenario; ten preferred.
Block by scenario/seed and randomize strategy order within blocks. Exclude the
same explicit warm-up interval and allow readiness/reset/cooldown between runs.

Every immutable raw run includes run_id, git commit, configuration hash, image
digest, strategy/scenario/seed, UTC start/end, Kubernetes version, host snapshot,
raw metric path and validation status. Missing required streams, saturation of
the generator, or manual intervention invalidate the run; retain all artifacts.

Partition runs in time order with disjoint train/validation/test sets. Feature
windows and forecast labels may not cross split boundaries. Freeze all settings
before final test. Report MAE/RMSE/sMAPE (both-zero contributes zero); if MAPE is
used, document excluded zero targets and their count.

Report latency, errors, SLO duration, decision/ready delays, scaling actions and
oscillation, pod-seconds, CPU-core-seconds and memory-GB-seconds. Distinguish
offered, admitted and completed demand to expose coordinated-omission bias.
Use paired/block-aware comparisons, effect sizes and uncertainty intervals;
avoid treating per-second samples as independent experimental repetitions.
