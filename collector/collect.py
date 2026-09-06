"""Capture an append-only engineering observation with explicit missing-stream checks."""

import argparse
import csv
import hashlib
import json
import math
import platform
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
import pyarrow as pa
import pyarrow.parquet as pq
import yaml
from kubernetes import client, config

from scripts.smoke import validate_target

NAMESPACE = "kavach-lab"
RATE = 'kavach_requests_total{job="payment-api"}'
CPU = 'kavach_container_cpu_seconds_total{job="payment-api"}'
MEM = 'kavach_container_memory_working_set_bytes{job="payment-api"}'
QUERIES = {
    "current_rps": f"sum(rate({RATE}[10s]))",
    "success_rps": 'sum(rate(kavach_requests_total{job="payment-api",status=~"2..|3.."}[10s])) or vector(0)',
    "error_rps": 'sum(rate(kavach_requests_total{job="payment-api",status=~"4..|5.."}[10s])) or vector(0)',
    "latency_mean_ms": '1000 * sum(rate(kavach_request_duration_seconds_sum{job="payment-api"}[10s])) / sum(rate(kavach_request_duration_seconds_count{job="payment-api"}[10s]))',
    **{
        f"latency_p{q}_ms": f'1000 * histogram_quantile({q / 100}, sum by(le)(rate(kavach_request_duration_seconds_bucket{{job="payment-api"}}[10s])))'
        for q in (50, 95, 99)
    },
    "cpu_usage_cores": f"sum(rate({CPU}[10s]))",
    "memory_bytes": f"sum({MEM})",
    "cpu_source_timestamp": 'min(kavach_container_sample_timestamp_seconds{job="payment-api"})',
    "memory_source_timestamp": 'min(kavach_container_sample_timestamp_seconds{job="payment-api"})',
    "app_source_timestamp": f"min(timestamp({RATE}))",
    "app_targets_up": 'sum(up{job="payment-api"})',
    "app_targets_count": 'count(up{job="payment-api"})',
    "cadvisor_up": 'min(up{job="cadvisor"})',
}

REQUIRED = (
    "timestamp",
    "current_rps",
    "success_rps",
    "error_rps",
    "cpu_usage_cores",
    "memory_bytes",
    "ready_replicas",
    "desired_replicas",
    "pending_replicas",
    "restart_count",
    "pod_start_events",
    "app_source_timestamp",
    "cpu_source_timestamp",
    "memory_source_timestamp",
    "app_targets_up",
    "app_targets_count",
    "cadvisor_up",
    "snapshot_duration_s",
)


def validate_rows(rows: list[dict], expected: int, interval: float) -> dict:
    reasons = []
    if len(rows) != expected:
        reasons.append(f"sample_count:{len(rows)}/{expected}")
    previous = None
    for index, row in enumerate(rows):
        for field in REQUIRED:
            value = row.get(field)
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                reasons.append(f"row:{index}:missing_or_invalid:{field}")
        stamp = row.get("timestamp")
        if isinstance(stamp, (int, float)):
            if previous is not None and not 0 < stamp - previous <= interval * 1.5:
                reasons.append(f"row:{index}:cadence_gap")
            previous = stamp
            for field in (
                "app_source_timestamp",
                "cpu_source_timestamp",
                "memory_source_timestamp",
            ):
                source = row.get(field)
                if isinstance(source, (int, float)) and not -1 <= stamp - source <= 6:
                    reasons.append(f"row:{index}:stale_or_future:{field}")
        duration = row.get("snapshot_duration_s")
        if isinstance(duration, (int, float)) and duration > interval:
            reasons.append(f"row:{index}:snapshot_exceeds_interval")
        if row.get("current_rps", 0) and row.get("current_rps", 0) > 0:
            for field in ("latency_mean_ms", "latency_p50_ms", "latency_p95_ms", "latency_p99_ms"):
                if row.get(field) is None or not math.isfinite(row[field]):
                    reasons.append(f"row:{index}:missing_latency:{field}")
        if row.get("cadvisor_up") != 1:
            reasons.append(f"row:{index}:cadvisor_unavailable")
        if row.get("app_targets_up") != row.get("app_targets_count") or (
            row.get("app_targets_up") or 0
        ) < (row.get("ready_replicas") or 0):
            reasons.append(f"row:{index}:incomplete_app_scrapes")
        if row.get("error"):
            reasons.append(f"row:{index}:collection_error:{row['error']}")
    return {
        "status": "PASS" if not reasons and rows else "INVALID",
        "sample_count": len(rows),
        "expected_samples": expected,
        "reasons": reasons,
    }


def prom_query(http: httpx.Client, query: str, timestamp: float):
    response = http.get("/api/v1/query", params={"query": query, "time": timestamp})
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "success":
        raise ValueError(f"Prometheus query failed: {payload}")
    result = payload["data"]["result"]
    if not result:
        return None
    if len(result) != 1:
        raise ValueError("Expected one aggregate Prometheus sample")
    number = float(result[0]["value"][1])
    return number if math.isfinite(number) else None


def make_clients(kubeconfig: Path):
    cfg = client.Configuration()
    config.load_kube_config(str(kubeconfig), context="kind-kavach-lab", client_configuration=cfg)
    # The isolated kind control plane must be published on literal loopback.
    validate_target(cfg.host.replace("https://", "http://", 1))
    api = client.ApiClient(cfg)
    core = client.CoreV1Api(api)
    namespace = core.read_namespace(NAMESPACE, _request_timeout=5)
    if namespace.metadata.labels.get("app.kubernetes.io/part-of") != "kavach-ai":
        raise ValueError("Namespace lacks Kavach testbed identity")
    return api, core, client.AppsV1Api(api)


def collect(
    folder: Path,
    duration: int,
    interval: int,
    prometheus: str,
    kubeconfig: Path,
    run_config: dict | None = None,
    start_utc: float | None = None,
):
    api, core, apps = make_clients(kubeconfig)
    version = client.VersionApi(api).get_code(_request_timeout=5).to_dict()
    initial_pods = core.list_namespaced_pod(
        NAMESPACE, label_selector="app=payment-api", _request_timeout=5
    )
    images = sorted(
        {s.image_id for p in initial_pods.items for s in (p.status.container_statuses or [])}
    )
    conf = {
        "duration_s": duration,
        "interval_s": interval,
        "prometheus": prometheus,
        "strategy": "STATIC",
        "scenario": "observability-smoke",
        "seed": 240005,
        "queries": QUERIES,
        "slo_p95_ms": 300,
        "slo_error_fraction": 0.01,
        "research_eligible": False,
    }
    if run_config:
        conf.update(run_config)
    (folder / "config.yaml").write_text(yaml.safe_dump(conf), encoding="utf-8")
    metadata = {
        "run_id": folder.name,
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "config_hash": hashlib.sha256(json.dumps(conf, sort_keys=True).encode()).hexdigest(),
        "strategy": "STATIC",
        "scenario": "observability-smoke",
        "seed": 240005,
        "start_utc": datetime.now(UTC).isoformat(),
        "image_digest": images,
        "kubernetes_version": version,
        "host": platform.platform(),
        "raw_metric_path": str(folder / "metrics.parquet"),
        "validity_status": "IN_PROGRESS",
        "research_eligible": False,
        "reason": "engineering observation; no Locust workload artifact yet",
    }
    metadata.update(strategy=conf["strategy"], scenario=conf["scenario"], seed=conf["seed"])
    (folder / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    rows = []
    seen_pods = {p.metadata.uid for p in initial_pods.items}
    seen_events = {}
    expected = duration // interval
    started = time.monotonic() + max(0, (start_utc or time.time()) - time.time())
    with (
        httpx.Client(
            base_url=prometheus, timeout=5, trust_env=False, follow_redirects=False
        ) as http,
        ThreadPoolExecutor(max_workers=8) as pool,
        (folder / "snapshots.jsonl").open("x", encoding="utf-8") as snapshots,
        (folder / "events.jsonl").open("x", encoding="utf-8") as event_file,
        (folder / "metrics.jsonl").open("x", encoding="utf-8") as raw,
    ):
        for index in range(expected):
            time.sleep(max(0, started + index * interval - time.monotonic()))
            tick = time.monotonic()
            stamp = time.time()
            row = {
                "run_id": folder.name,
                "timestamp": stamp,
                "strategy": conf["strategy"],
                "scenario": conf["scenario"],
                "random_seed": conf["seed"],
                "controller_mode": "OFF",
                "forecast_rps_horizon": None,
                "forecast_error": None,
                "burst_class": None,
                "burst_score": None,
                "scaling_reason": None,
                "git_commit": metadata["git_commit"],
            }
            try:
                pending = {
                    key: pool.submit(prom_query, http, query, stamp)
                    for key, query in QUERIES.items()
                }
                pods = core.list_namespaced_pod(
                    NAMESPACE, label_selector="app=payment-api", _request_timeout=5
                )
                deployment = apps.read_namespaced_deployment(
                    "payment-api", NAMESPACE, _request_timeout=5
                )
                events = core.list_namespaced_event(NAMESPACE, _request_timeout=5)
                snapshots.write(
                    json.dumps(
                        {
                            "timestamp": stamp,
                            "pods": api.sanitize_for_serialization(pods),
                            "deployment": api.sanitize_for_serialization(deployment),
                        }
                    )
                    + "\n"
                )
                snapshots.flush()
                row.update({key: future.result() for key, future in pending.items()})
                row["ready_replicas"] = sum(
                    any(
                        c.type == "Ready" and c.status == "True"
                        for c in (p.status.conditions or [])
                    )
                    for p in pods.items
                )
                row["desired_replicas"] = deployment.spec.replicas
                row["pending_replicas"] = sum(p.status.phase == "Pending" for p in pods.items)
                row["restart_count"] = sum(
                    s.restart_count for p in pods.items for s in (p.status.container_statuses or [])
                )
                row["pod_start_events"] = sum(p.metadata.uid not in seen_pods for p in pods.items)
                seen_pods.update(p.metadata.uid for p in pods.items)
                row["cpu_utilization_pct"] = (
                    row["cpu_usage_cores"] / (0.25 * max(1, row["ready_replicas"])) * 100
                    if row.get("cpu_usage_cores") is not None
                    else None
                )
                row["scaling_event"] = bool(
                    rows and rows[-1].get("desired_replicas") != row["desired_replicas"]
                )
                row["current_slo_violation"] = None
                if row.get("current_rps") is not None and row.get("error_rps") is not None:
                    row["current_slo_violation"] = (row.get("latency_p95_ms") or 0) >= 300 or row[
                        "error_rps"
                    ] / max(row["current_rps"], 1e-9) >= 0.01
                for event in events.items:
                    if seen_events.get(event.metadata.uid) != event.metadata.resource_version:
                        event_file.write(
                            json.dumps(
                                {
                                    "observed_at": stamp,
                                    "event": api.sanitize_for_serialization(event),
                                }
                            )
                            + "\n"
                        )
                        seen_events[event.metadata.uid] = event.metadata.resource_version
                event_file.flush()
            except Exception as exc:  # noqa: BLE001 -- retain invalid samples and reasons
                row["error"] = f"{type(exc).__name__}: {exc}"
            row["snapshot_duration_s"] = time.monotonic() - tick
            rows.append(row)
            raw.write(json.dumps(row, allow_nan=False) + "\n")
            raw.flush()
    warmup_rows = conf.get("warmup_s", 0) // interval
    validation = validate_rows(rows[warmup_rows:], expected - warmup_rows, interval)
    validation["excluded_warmup_rows"] = warmup_rows
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, folder / "metrics.parquet")
    fields = sorted({key for row in rows for key in row})
    with (folder / "metrics.csv").open("x", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    metadata.update(end_utc=datetime.now(UTC).isoformat(), validity_status=validation["status"])
    (folder / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (folder / "validation.json").write_text(json.dumps(validation, indent=2), encoding="utf-8")
    api.close()
    return validation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--interval", type=int, default=2)
    parser.add_argument("--prometheus", default="http://127.0.0.1:9090")
    parser.add_argument("--kubeconfig", type=Path, default=Path("infrastructure/kubeconfig"))
    parser.add_argument("--output", type=Path, default=Path("experiments/raw"))
    args = parser.parse_args()
    if (
        not 2 <= args.interval <= 10
        or args.duration < args.interval
        or args.duration % args.interval
    ):
        parser.error("duration must be a positive multiple of interval (2..10 seconds)")
    folder = args.output / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-obs-" + uuid4().hex[:8]
    )
    folder.mkdir(parents=True, exist_ok=False)
    try:
        result = collect(
            folder, args.duration, args.interval, validate_target(args.prometheus), args.kubeconfig
        )
    except Exception as exc:  # noqa: BLE001 -- preserve failures including preflight
        result = {"status": "INVALID", "reasons": [f"{type(exc).__name__}: {exc}"]}
        (folder / "validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"folder": str(folder), **result}, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
