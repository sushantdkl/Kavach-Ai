"""Run one local development/calibration experiment and retain every outcome."""

import argparse
import csv
import hashlib
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import yaml
from kubernetes import client

from collector.collect import NAMESPACE, collect, make_clients
from workload.trace import compile_trace, trace_hash, validate_config

KUBECTL = [
    "kubectl",
    "--kubeconfig",
    "infrastructure/kubeconfig",
    "--context",
    "kind-kavach-lab",
    "-n",
    NAMESPACE,
]


def command(*args, timeout=30, check=True):
    return subprocess.run(
        [*KUBECTL, *args], capture_output=True, text=True, timeout=timeout, check=check
    )


def wait_file(pod, file, seconds=60):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        result = command("exec", pod, "--", "cat", f"/data/{file}", check=False)
        if result.returncode == 0:
            return json.loads(result.stdout)
        time.sleep(1)
    raise TimeoutError(f"Load pod did not produce {file}")


def run(scenario, strategy, replicas, output):
    cfg = validate_config(yaml.safe_load(scenario.read_text()))
    if cfg["warmup_s"] < 20 or cfg["warmup_s"] % 2 or cfg["duration_s"] % 2:
        raise ValueError("Experiments require >=20s warmup and even warmup/duration")
    if subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"], text=True
    ).strip():
        raise RuntimeError("Commit tracked source changes before experiments")
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    folder = output / run_id
    folder.mkdir(parents=True, exist_ok=False)
    pod_name = "load-" + uuid4().hex[:12]
    reasons = []
    api = core = None
    created_pod = False
    exported = False
    manifest = None
    try:
        api, core, apps = make_clients(Path("infrastructure/kubeconfig"))
        autoscaling = client.AutoscalingV2Api(api)
        existing = autoscaling.list_namespaced_horizontal_pod_autoscaler(NAMESPACE)
        for hpa in existing.items:
            if hpa.spec.scale_target_ref.name == "payment-api":
                autoscaling.delete_namespaced_horizontal_pod_autoscaler(
                    hpa.metadata.name, NAMESPACE
                )
        apps.patch_namespaced_deployment_scale(
            "payment-api", NAMESPACE, {"spec": {"replicas": replicas}}
        )
        stable_start = None
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            deployment = apps.read_namespaced_deployment("payment-api", NAMESPACE)
            if (
                deployment.status.ready_replicas == replicas
                and deployment.status.replicas == replicas
            ):
                stable_start = stable_start or time.monotonic()
                if time.monotonic() - stable_start >= 10:
                    break
            else:
                stable_start = None
            time.sleep(1)
        else:
            raise TimeoutError("Payment replica state never stabilized")
        if strategy == "HPA_CANDIDATE":
            command("apply", "-f", "infrastructure/k8s/hpa/candidate.yaml")
        deployment = apps.read_namespaced_deployment("payment-api", NAMESPACE)
        (folder / "deployment.json").write_text(
            json.dumps(api.sanitize_for_serialization(deployment), indent=2)
        )
        (folder / "hpa.json").write_text(
            json.dumps(
                api.sanitize_for_serialization(
                    autoscaling.list_namespaced_horizontal_pod_autoscaler(NAMESPACE)
                ),
                indent=2,
            )
        )
        service = core.read_namespaced_service("payment-api", NAMESPACE)
        if service.spec.type != "ClusterIP" or service.spec.selector != {"app": "payment-api"}:
            raise RuntimeError("Unexpected payment Service; refusing workload")
        trace = compile_trace(cfg)
        (folder / "offered-trace.jsonl").write_text("".join(json.dumps(r) + "\n" for r in trace))
        core.create_namespaced_config_map(
            NAMESPACE,
            client.V1ConfigMap(
                metadata=client.V1ObjectMeta(name=pod_name),
                immutable=True,
                data={"scenario.json": json.dumps(cfg)},
            ),
        )
        manifest = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": pod_name,
                "namespace": NAMESPACE,
                "labels": {"app": "kavach-load", "run-id": run_id},
            },
            "spec": {
                "restartPolicy": "Never",
                "automountServiceAccountToken": False,
                "securityContext": {
                    "runAsUser": 10001,
                    "runAsGroup": 10001,
                    "fsGroup": 10001,
                    "runAsNonRoot": True,
                },
                "containers": [
                    {
                        "name": "locust",
                        "image": "kavach-workload:dev",
                        "imagePullPolicy": "Never",
                        "env": [{"name": "KAVACH_SERVICE_IP", "value": service.spec.cluster_ip}],
                        "resources": {
                            "requests": {"cpu": "100m", "memory": "128Mi"},
                            "limits": {"cpu": "1500m", "memory": "384Mi"},
                        },
                        "volumeMounts": [
                            {"name": "config", "mountPath": "/config", "readOnly": True},
                            {"name": "output", "mountPath": "/data"},
                        ],
                    }
                ],
                "volumes": [
                    {"name": "config", "configMap": {"name": pod_name}},
                    {"name": "output", "emptyDir": {"sizeLimit": "256Mi"}},
                ],
            },
        }
        (folder / "load-pod.json").write_text(json.dumps(manifest, indent=2))
        core.create_namespaced_pod(NAMESPACE, manifest)
        created_pod = True
        wait_file(pod_name, "ready.json", 120)
        load_pod = core.read_namespaced_pod(pod_name, NAMESPACE)
        image_id = load_pod.status.container_statuses[0].image_id
        start = time.time() + 8
        command(
            "exec",
            pod_name,
            "--",
            "python",
            "-c",
            "from pathlib import Path; import sys; Path('/data/go.json').write_text(sys.argv[1])",
            json.dumps({"start_utc": start}),
        )
        run_config = {
            "scenario": cfg["name"],
            "seed": cfg["seed"],
            "strategy": strategy,
            "warmup_s": cfg["warmup_s"],
            "workload": cfg,
            "trace_hash": trace_hash(trace),
            "load_image_digest": image_id,
            "purpose": "calibration",
            "research_eligible": False,
        }
        print(
            json.dumps(
                {
                    "run_id": run_id,
                    "strategy": strategy,
                    "scenario": cfg["name"],
                    "duration_s": cfg["duration_s"],
                    "folder": str(folder),
                }
            ),
            flush=True,
        )
        validation = collect(
            folder,
            cfg["duration_s"],
            2,
            "http://127.0.0.1:9090",
            Path("infrastructure/kubeconfig"),
            run_config=run_config,
            start_utc=start,
        )
        reasons.extend(validation["reasons"])
        finished = wait_file(pod_name, "exit.json", 45)
        command("cp", f"{pod_name}:/data", str(folder / "locust"), timeout=60)
        exported = True
        replay = json.loads((folder / "locust/replay.json").read_text())
        requests = [
            json.loads(line) for line in (folder / "locust/requests.jsonl").read_text().splitlines()
        ]
        if not replay["generator_valid"] or len(requests) != len(trace):
            reasons.append("generator_drops_or_missing_requests")
        if replay["trace_hash"] != run_config["trace_hash"]:
            reasons.append("trace_hash_mismatch")
        if finished["exit_code"] != 0:
            reasons.append(f"locust_exit:{finished['exit_code']}")
        with (folder / "locust/locust_exceptions.csv").open() as exception_file:
            if list(csv.DictReader(exception_file)):
                reasons.append("locust_runtime_exceptions")
        measured = [r for r in requests if not r["dropped"] and r["offset_s"] >= cfg["warmup_s"]]
        latencies = sorted(r["latency_ms"] for r in measured)
        errors = sum(r["status"] < 200 or r["status"] >= 400 for r in measured)
        summary = {
            "run_id": run_id,
            "strategy": strategy,
            "scenario": cfg["name"],
            "requests": len(measured),
            "errors": errors,
            "error_fraction": errors / len(measured) if measured else None,
            "mean_latency_ms": sum(latencies) / len(latencies) if latencies else None,
            "p95_latency_ms": latencies[int(0.95 * (len(latencies) - 1))] if latencies else None,
            "p99_latency_ms": latencies[int(0.99 * (len(latencies) - 1))] if latencies else None,
            "trace_hash": run_config["trace_hash"],
            "purpose": "calibration",
        }
        (folder / "summary.json").write_text(json.dumps(summary, indent=2))
    except Exception as exc:  # noqa: BLE001 -- retain failed runs
        reasons.append(f"{type(exc).__name__}: {exc}")
    finally:
        if created_pod and not exported:
            try:
                command("cp", f"{pod_name}:/data", str(folder / "locust"), timeout=30)
                exported = True
            except Exception as exc:  # noqa: BLE001 -- preserve export failure
                reasons.append(f"artifact_export_failed:{exc}")
        result = {
            "run_id": run_id,
            "status": "PASS" if not reasons else "INVALID",
            "reasons": reasons,
            "research_eligible": False,
            "purpose": "calibration",
        }
        (folder / "validation.json").write_text(json.dumps(result, indent=2))
        metadata_path = folder / "metadata.json"
        metadata = (
            json.loads(metadata_path.read_text()) if metadata_path.exists() else {"run_id": run_id}
        )
        metadata.update(validity_status=result["status"], end_utc=datetime.now(UTC).isoformat())
        metadata_path.write_text(json.dumps(metadata, indent=2))
        if core and exported:
            core.delete_namespaced_pod(pod_name, NAMESPACE, grace_period_seconds=1)
            core.delete_namespaced_config_map(pod_name, NAMESPACE)
        if api:
            api.close()
        (folder / "checksums.json").write_text(
            json.dumps(
                {
                    str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in folder.rglob("*")
                    if p.is_file()
                },
                indent=2,
            )
        )
        print(json.dumps({"folder": str(folder), **result}, indent=2), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--strategy", choices=("STATIC", "HPA_CANDIDATE"), default="STATIC")
    parser.add_argument("--replicas", type=int, choices=range(1, 7), default=1)
    parser.add_argument("--output", type=Path, default=Path("experiments/raw"))
    args = parser.parse_args()
    result = run(args.scenario, args.strategy, args.replicas, args.output)
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
