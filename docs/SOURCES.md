# Source audit

The supplied baseline remains intact. Its literature claims are not silently
promoted into verified citations. Before thesis writing, identify each paper
with title/authors/DOI and verify the claim against the original publication.
The unnamed 2026 LLM paper is unresolved; do not invent a citation.

Verified implementation references, accessed 2026-09-06:

| Source | Used for |
|---|---|
| https://fastapi.tiangolo.com/deployment/docker/ | Container topology; single process with Kubernetes replication |
| https://kind.sigs.k8s.io/docs/user/quick-start/ | Windows installation and cluster creation |
| https://kind.sigs.k8s.io/docs/user/known-issues/ | Docker Linux container requirement |

## Landscape audit, 2026-09-06

| Topic | Primary source and supported scope |
|---|---|
| HPA | https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/ — resource/custom metrics and configurable stabilization/rates. Version-specific tolerance must be checked on our 1.34 cluster. |
| PredictKube | https://keda.sh/docs/2.20/scalers/predictkube/ — predictive SaaS integration; recommends 7–14 days of history, not a universal hard seven-day requirement. |
| AWS | https://docs.aws.amazon.com/autoscaling/ec2/userguide/predictive-scaling-policy-overview.html — forecast-only validation, predictive scale-out, separate dynamic scale-in. |
| Azure | https://learn.microsoft.com/en-us/azure/azure-monitor/autoscale/autoscale-predictive — cyclical VM CPU demand, minimum seven days, forecast-only and predictive scale-out. |
| CAST AI | https://docs.cast.ai/docs/workload-autoscaling-configuration — predictive vertical CPU allocation and HPA exclusion; do not generalize that exclusion to all vertical/horizontal coordination. |
| BAScaler / BASE | Meng, Tong, Wu, Pan, Yu, Jiang, arXiv:2402.12962. The current v2 title is BASE: Burst-Adaptive Autoscaling via Stacked Ensembles for SLO Assurance and Cost Efficiency. Revised 2 March 2026; related DOI 10.1109/TSC.2026.3668105. https://arxiv.org/abs/2402.12962 — abstract supports burst-adaptive prior work; no performance numbers copied into Kavach. |
| YoYo | Ronen Ben David and Anat Bremler Barr, Kubernetes Autoscaling: YoYo Attack Vulnerability and Mitigation, CLOSER 2021, DOI 10.5220/0010397900340044. https://arxiv.org/abs/2105.00542 — periodic scaling/performance risk; their node/VM experiments differ from our fixed-node pod-only testbed. |
| Candidate unnamed LLM paper | From reactive to predictive: A pattern-Aware framework for kubernetes autoscaling with large language model integration. https://www.sciencedirect.com/science/article/abs/pii/S0164121226000944 — publisher search abstract matches the baseline description. Full publisher page unavailable to browser retrieval; authors/DOI/method details remain unverified. No numerical claim is adopted. |

General drift/survey claims still need specific papers. Product documents and
paper abstracts justify design context; they do not establish Kavach's novelty
or validate its experiments. Preserve the distinction between abstract review
and full methodological review.
