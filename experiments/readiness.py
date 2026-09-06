"""Measure scale-request to ready delay on the isolated testbed with no workload running."""

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from kubernetes import client

from collector.collect import NAMESPACE, make_clients


def wait_replicas(apps, count):
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        deployment = apps.read_namespaced_deployment("payment-api", NAMESPACE, _request_timeout=5)
        if deployment.status.ready_replicas == count and deployment.status.replicas == count:
            return
        time.sleep(0.2)
    raise TimeoutError(f"Did not reach {count} ready replicas")


def main():
    api, core, apps = make_clients(Path("infrastructure/kubeconfig"))
    if core.list_namespaced_pod(NAMESPACE, label_selector="app=kavach-load").items:
        raise RuntimeError("Load pod exists; readiness calibration requires idle testbed")
    if client.AutoscalingV2Api(api).list_namespaced_horizontal_pod_autoscaler(NAMESPACE).items:
        raise RuntimeError("Remove the experiment HPA before manual readiness calibration")
    folder = Path("experiments/raw") / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-readiness-" + uuid4().hex[:8]
    )
    folder.mkdir(parents=True, exist_ok=False)
    with (folder / "observations.jsonl").open("x") as output:
        try:
            for repetition in range(5):
                apps.patch_namespaced_deployment_scale(
                    "payment-api", NAMESPACE, {"spec": {"replicas": 1}}
                )
                wait_replicas(apps, 1)
                time.sleep(3)
                start_utc, start = time.time(), time.monotonic()
                apps.patch_namespaced_deployment_scale(
                    "payment-api", NAMESPACE, {"spec": {"replicas": 2}}
                )
                wait_replicas(apps, 2)
                row = {
                    "repetition": repetition,
                    "request_utc": start_utc,
                    "ready_utc": time.time(),
                    "decision_to_ready_s": time.monotonic() - start,
                    "poll_resolution_s": 0.2,
                    "pods": api.sanitize_for_serialization(
                        core.list_namespaced_pod(NAMESPACE, label_selector="app=payment-api")
                    ),
                }
                output.write(json.dumps(row) + "\n")
                output.flush()
                print(json.dumps({k: v for k, v in row.items() if k != "pods"}), flush=True)
        finally:
            apps.patch_namespaced_deployment_scale(
                "payment-api", NAMESPACE, {"spec": {"replicas": 1}}
            )
            api.close()
    print(str(folder), flush=True)


if __name__ == "__main__":
    main()
