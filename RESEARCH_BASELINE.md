# Kavach AI — Research Baseline and 2026 Landscape

**Student:** Sushant Dhakal (240005)  
**Project:** AI-Powered Predictive Autoscaling for Resilient Digital Payment APIs Under Flash-Crowd and Attack-Like Traffic  
**Purpose of this document:** Freeze the market/research understanding that should guide implementation.

---

## 1. What already exists

### Kubernetes HPA
Kubernetes Horizontal Pod Autoscaler is the unavoidable baseline. It supports CPU, memory, and custom/external metrics, configurable scale-up/scale-down policies, stabilization windows, and tolerance. Modern HPA is much more capable than a simplistic "CPU > 60% then add pod" description.

Implication for Kavach AI:
- The HPA baseline must be **tuned**, not intentionally weak.
- We must report its exact configuration.
- We should use the same min/max replicas and resource requests across all strategies.
- HPA behavior, startup/readiness, stabilization, and metric timing must be logged.

### KEDA
KEDA supports event-driven autoscaling and Prometheus-based scaling. It can scale from application-level metrics such as request rate rather than CPU alone.

Implication:
- A Prometheus/KEDA request-rate baseline is stronger than CPU-only HPA.
- If time allows, include it as an optional fourth strategy or sensitivity check.

### PredictKube / KEDA Predictive Scaler
KEDA has a PredictKube scaler that uses Prometheus history and an external predictive service. Its design assumes substantial historical data, commonly a seven-day window.

Implication:
- "Predictive autoscaling exists" is not a research gap.
- Kavach's differentiator must be short-horizon, burst-aware, reproducible, locally controlled experimentation rather than generic prediction.

### AWS Predictive Scaling
AWS provides predictive scaling with a forecast-only mode before enabling scale actions. It combines predictive scale-out with reactive mechanisms for scale-in/safety.

Implication:
- Kavach should have **shadow mode** before actuation.
- Prediction should not be trusted as the only safety mechanism.
- Scale-down should be conservative and based on observed demand/stability.

### Azure Predictive Autoscale
Azure predictive autoscale is aimed at cyclical VM workloads, requires historical data, supports forecast-only validation, and scales out predictively while standard autoscaling handles scale-in.

Implication:
- Short burst traffic is a different problem from long-cycle predictive VM scaling.
- Kavach should explicitly evaluate burst/flash-crowd behavior and not claim to replace commercial predictive autoscaling.

### CAST AI
CAST AI provides horizontal and vertical workload autoscaling. Its predictive workload feature focuses on historical, predictable resource patterns and predictive vertical resource sizing; predictive scaling and horizontal scaling have compatibility constraints.

Implication:
- We should keep Kavach focused on **horizontal replica decisions** for a single experimental service.
- Combining VPA + HPA + predictive horizontal control would unnecessarily explode thesis scope.

---

## 2. Important research findings

### Burst-aware predictive autoscaling
Prior research such as BAScaler shows that burst-aware policies can reduce SLO violations and overprovisioning by distinguishing workload behavior and adapting scaling responses.

This means:
- Burst awareness is not itself novel.
- Our contribution must come from the combination of:
  1. a reproducible payment-style API testbed,
  2. short-horizon forecasting,
  3. burst/overload classification,
  4. attack-cost-aware safeguards,
  5. transparent controller decisions,
  6. fair repeated comparison against tuned baselines.

### Yo-Yo / EDoS risk
Research on Yo-Yo attacks shows that autoscaling can be manipulated by periodic bursts, producing oscillation, performance degradation, and economic cost amplification.

This is highly relevant to Kavach.

Important correction:
Kavach **must not assume every large burst deserves more replicas**.

The system should distinguish:
- legitimate flash-crowd-like bursts,
- noisy transient spikes,
- repeated oscillatory bursts,
- sustained overload,
- recovery.

The system should not claim to perform full DDoS detection. That would be another thesis.

### SLO- and cost-aware autoscaling
Recent work increasingly uses application-level signals such as latency/SLO violations and cost rather than relying only on CPU.

Implication:
Kavach should use multiple signals:
- request rate,
- CPU,
- p95 latency,
- error rate,
- current replica count,
- startup/readiness delay,
- burst score.

CPU alone is insufficient.

### Drift and uncertainty
Recent predictive-autoscaling surveys highlight drift-aware and uncertainty-aware controllers as an open direction.

A full drift-learning system is probably too large for this thesis, but we should:
- detect forecast error growth,
- log confidence/error,
- fall back to reactive scaling when prediction becomes unreliable.

---

## 3. About the LLM requirement

A 2026 paper on predictive horizontal pod autoscaling uses LLM-based workload-pattern classification/model selection and reports improved forecasting accuracy over a single universal model.

This is relevant, but there is a trap:

**Training a real large language model from scratch is not sensible for this thesis.**
Reasons:
- You do not have a language-scale corpus.
- The workload is numeric time-series, not natural language.
- Training a foundation LLM would consume far more compute than the autoscaling experiment.
- It would make the thesis harder to defend because the LLM is not necessary to solve the main control problem.

### Recommended interpretation of "our own model"

Build two AI layers that are genuinely yours:

1. **Core forecasting models**
   - naive last-value baseline
   - Random Forest
   - XGBoost
   - optional lightweight temporal model

2. **Kavach Pattern Intelligence**
   - train a **small transformer or MLP/gradient-boosted pattern classifier from your own synthetic workload traces**
   - classify:
     - steady
     - gradual/ramp
     - flash burst
     - oscillatory/Yo-Yo-like
     - sustained overload
     - recovery
   - optionally use that pattern to select policy/model parameters

Do not call this an LLM if it is not large or language-based.

### Optional local SLM/LLM layer
If a language-model component is mandatory, use it only as a **non-actuating advisor/explainer**:
- input: structured scaling event summary
- output: human-readable explanation / pattern label / diagnostic note
- never directly change Kubernetes replicas
- keep it offline/local where practical
- evaluate its classification/explanation separately

This protects the core thesis from becoming dependent on an unreliable generative model.

---

## 4. Stronger research gap

Weak gap:
> Current autoscaling lacks intelligence.

This is false/too broad.

Better gap:
> Existing production and research autoscaling approaches already include reactive, event-driven, predictive, burst-aware, and cost-aware techniques. However, there remains room for a small, reproducible, locally controlled experimental framework that evaluates whether short-horizon workload forecasting combined with burst classification and safety-aware horizontal scaling can improve latency, reliability, scaling delay, and resource efficiency for a latency-sensitive payment-style API under sudden legitimate and attack-like traffic, compared with properly tuned reactive baselines.

That is narrow enough to defend.

---

## 5. Recommended research question

### RQ1
How does a short-horizon, burst-aware predictive horizontal autoscaling policy affect p95 latency, error rate, scaling delay, SLO violations, scaling stability, and resource consumption for a simulated digital-payment API under steady, ramp, flash-crowd, oscillatory, and attack-like workloads compared with static allocation and tuned reactive autoscaling?

### RQ2
How can attack-like workload experiments and AI-assisted autoscaling be designed and reported safely so that they use only isolated synthetic traffic, avoid real financial information and external targets, and provide transparent limits on reliability and generalisability?

---

## 6. Refined hypotheses

### H1 — Forecasting
For short-horizon workload prediction, trained tree-based ensemble models will achieve lower forecast error than a naive last-value baseline on unseen, time-ordered workload runs.

Primary target:
- future request rate at t + H

Secondary derived/auxiliary signals:
- overload risk
- burst class

Metrics:
- MAE
- RMSE
- sMAPE preferred over MAPE when traffic can approach zero
- MAPE retained if required by the proposal, with zero-handling documented

### H2 — Controller
Under bursty workloads, Kavach AI will reduce p95 latency, error rate, SLO-violation duration, and effective scaling delay compared with static allocation and tuned reactive autoscaling without causing materially higher normalized resource consumption or scaling oscillation.

---

## 7. Baselines

Mandatory:
1. Static fixed replica count
2. Tuned Kubernetes HPA
3. Kavach AI

Strong optional baseline:
4. KEDA + Prometheus request-rate scaler

External predictive benchmark, optional only:
5. PredictKube, if reproducible access is available and methodology remains fair

Do not make PredictKube mandatory because it relies on an external predictive service and longer historical windows that may not match a student-controlled experiment.

---

## 8. Workload taxonomy

Every strategy must receive the exact same seeded workload trace.

W0 — idle/warm-up  
W1 — steady normal load  
W2 — gradual ramp  
W3 — legitimate flash crowd  
W4 — repeated short bursts  
W5 — oscillatory / Yo-Yo-like local synthetic trace  
W6 — sustained overload  
W7 — hybrid normal + abnormal bursts  
W8 — recovery / demand collapse

Safety:
- local/private test environment only
- rate ceilings
- no public IP target
- no real wallet/payment provider
- no credential attack behavior
- no exploit payloads
- synthetic transaction records only

---

## 9. What "attack-aware" should mean

Do not build a DDoS mitigation product.

Kavach should only be **attack-cost-conscious**:
- detect suspicious oscillatory/burst structure
- cap scale-up aggressiveness
- preserve a minimum reliability floor
- log why a cap/fallback occurred
- avoid repeated scale-up/scale-down thrashing

A true security product would need:
- source/IP reputation
- WAF/bot mitigation
- rate limiting
- network telemetry
- attack attribution

Those are out of scope.

---

## 10. Evaluation metrics

### Forecasting
- MAE
- RMSE
- MAPE/sMAPE
- directional accuracy (optional)
- burst recall/precision for pattern classifier

### API/SLO
- average latency
- p50
- p95
- p99
- throughput
- HTTP 5xx/error rate
- timeout rate
- SLO-violation duration

### Scaling
- trigger-to-decision delay
- decision-to-ready delay
- effective scaling delay
- number of scale-ups
- number of scale-downs
- replica oscillation count
- overprovisioned pod-seconds
- underprovisioned seconds

### Resource efficiency
- pod-seconds
- CPU-core-seconds
- memory-GB-seconds
- normalized resource cost index

Use a normalized cost model for local experiments rather than pretending local Minikube costs equal commercial cloud billing.

---

## 11. Experimental validity rules

- Same Docker image for all methods.
- Same Kubernetes cluster configuration.
- Same pod resource requests/limits.
- Same min/max replicas.
- Same workload trace/seed.
- Same readiness/startup probes.
- Same measurement interval.
- Same test duration.
- Warm-up period excluded consistently.
- Cool-down/reset cluster state between runs.
- Time-ordered train/validation/test partition.
- No random row-level split across adjacent timestamps.
- Repeat each workload/strategy combination multiple times.
- Report mean, median, standard deviation, and confidence intervals where appropriate.
- Prefer non-parametric comparison if assumptions for parametric tests are not met.

---

## 12. Recommended implementation principle

**Predict demand; do not let ML directly invent replica counts.**

Pipeline:

metrics
→ feature engineering
→ short-horizon demand forecast
→ workload/burst classification
→ capacity mapping
→ safety guardrails
→ replica recommendation
→ shadow mode
→ optional actuation
→ feedback/logging

This makes every decision inspectable.

---

## 13. Key design principle

Kavach AI is not:
- an LLM project,
- a DDoS protection system,
- a payment gateway,
- a replacement for HPA,
- a commercial cloud optimizer.

Kavach AI is:
> a controlled research artefact for testing whether short-horizon prediction + burst intelligence + safety-aware horizontal scaling improves a latency-sensitive payment-style Kubernetes workload under sudden demand.
