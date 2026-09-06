# Kavach AI — Read This First: Student Understanding Guide

This is the conceptual map you should understand before coding.

## 1. What problem are you actually solving?

A payment API can suddenly receive more requests than its current pods can serve.

Reactive HPA:
1. traffic increases
2. CPU/metric increases
3. HPA notices
4. HPA requests more pods
5. pods start
6. capacity becomes available

The problem is the delay between step 1 and step 6.

Kavach asks:
Can we predict the near-future workload early enough to start pods before users suffer?

But there is a second problem:
If every burst causes aggressive scaling, abnormal repeated bursts can waste resources and cause oscillation.

So Kavach adds:
- short-horizon forecast
- burst classification
- safety policy

## 2. Why not just use XGBoost to predict pods?

Because `7 pods` is not a meaningful scientific target by itself.

It mixes:
- demand prediction
- per-pod capacity
- SLO choice
- safety policy

Separating them makes the system explainable:

Forecast:
> 180 RPS expected in 10 seconds

Capacity model:
> one pod safely handles 40 RPS

Controller:
> 5 pods required

Safety:
> current oscillatory burst; cap this step to +2

Final:
> scale 3 → 5, reason=OSCILLATION_GUARDED_CAPACITY_DEFICIT

That is defensible.

## 3. What is the AI?

There are two different AI questions.

### Forecasting
What will demand be shortly in the future?

### Pattern intelligence
What kind of workload behavior is happening?

The controller itself should be mostly deterministic logic around those model outputs.

## 4. Why does the horizon matter?

Suppose a new pod needs 8 seconds to become ready.

Predicting 1 second ahead is not useful.
Predicting 10 seconds ahead may be useful.
Predicting 10 minutes ahead may be inaccurate for bursts.

Therefore you measure pod readiness first, then test horizons such as 5/10/15/30 seconds.

## 5. What is HPA?

Kubernetes HPA adjusts replicas from observed metrics.

Modern HPA supports:
- CPU/memory/custom metrics
- scaling policies
- stabilization windows
- tolerance

Your thesis must compare against a fair HPA.

## 6. What is KEDA?

KEDA can scale from event/application metrics such as Prometheus request rate.

It is useful because it proves "reactive autoscaling" does not have to mean CPU-only.

## 7. What is shadow mode?

The model says what it *would* do, but it does not touch Kubernetes.

This lets you inspect:
- forecast errors
- bad scale recommendations
- false pre-scaling
- instability

Commercial predictive systems use similar forecast-only ideas.

## 8. What is the attack-like part?

You are not attacking anything.

You reproduce a local time-series shape:
normal → burst → drop → burst → drop

The research question is:
How does the autoscaler behave under that shape?

This is safe when kept inside the isolated testbed.

## 9. What does "burst aware" mean?

The system uses recent history to detect whether traffic is:
- stable
- rising gradually
- suddenly bursting
- oscillating
- remaining overloaded
- recovering

Then the controller changes aggressiveness.

## 10. What is resource efficiency?

Because you are local, do not claim exact AWS cost savings.

Measure:
- pod-seconds
- CPU-core-seconds
- memory-GB-seconds

Then create a normalized cost/resource index.

## 11. What result would prove Kavach is useful?

Not simply "Kavach has lower latency."

You want a trade-off:

Kavach:
- lower p95/SLO violations
- lower errors
- earlier useful scale-up
- not much more resource use
- less/no worse oscillation

A strategy that gets perfect latency by always running maximum pods is not intelligent.

## 12. What if Kavach loses?

That is still a valid thesis.

Possible finding:
- HPA performs similarly under steady/ramp load
- predictive scaling helps only flash crowds
- prediction becomes unreliable under chaotic/oscillatory traces
- guardrails reduce EDoS-like resource growth but slightly worsen latency

That is actually a more credible research result than claiming AI wins everywhere.

## 13. Why not train our own LLM from scratch?

Because the problem is numerical time-series.

A language model requires huge text data and compute.
It would not automatically make the autoscaler better.

What we can train ourselves:
- RF/XGBoost forecast
- burst classifier
- small transformer time-series model

If a language model is required, keep it as an advisor/explainer, not the scaling brain.

## 14. What should you learn first?

In order:

1. Docker
2. Kubernetes Pod/Deployment/Service
3. resource requests/limits
4. readiness/startup probes
5. HPA
6. Prometheus metrics
7. Locust
8. time-series dataset construction
9. leakage-safe train/test split
10. RF/XGBoost forecasting
11. controller loops
12. statistical evaluation

## 15. Your first practical milestone

You have succeeded at Milestone 1 when you can show:

Locust traffic
→ FastAPI running inside Kubernetes
→ Prometheus captures RPS/latency/CPU
→ HPA changes replica count
→ all metrics are exported for one run

Only then start predictive ML.
