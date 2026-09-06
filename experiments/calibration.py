"""Summarize per-stage capacity evidence without silently selecting final parameters."""

import argparse
import json
import statistics
from pathlib import Path

import yaml


def summarize(folder):
    validation = json.loads((folder / "validation.json").read_text())
    config = yaml.safe_load((folder / "config.yaml").read_text())
    requests = [
        json.loads(line) for line in (folder / "locust/requests.jsonl").read_text().splitlines()
    ]
    stages = []
    elapsed = 0
    for stage in config["workload"]["stages"]:
        # Exclude the first 10s of each step, declared here before calibration runs.
        left = elapsed + 10
        right = elapsed + stage["duration_s"]
        rows = [r for r in requests if left <= r["offset_s"] < right]
        dispatched = [r for r in rows if not r["dropped"]]
        latencies = sorted(r["latency_ms"] for r in dispatched)
        errors = sum(r["status"] < 200 or r["status"] >= 400 for r in dispatched)
        stages.append(
            {
                "rps": stage["rps"],
                "start_s": left,
                "end_s": right,
                "offered": len(rows),
                "dropped": len(rows) - len(dispatched),
                "error_fraction": errors / len(dispatched) if dispatched else None,
                "mean_latency_ms": statistics.mean(latencies) if latencies else None,
                "p95_latency_ms": latencies[int(0.95 * (len(latencies) - 1))]
                if latencies
                else None,
                "p99_latency_ms": latencies[int(0.99 * (len(latencies) - 1))]
                if latencies
                else None,
            }
        )
        elapsed = right
    return {
        "run_id": folder.name,
        "validity": validation["status"],
        "purpose": "capacity calibration, not final test",
        "stages": stages,
        "parameters_frozen": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = summarize(args.run)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as output:
            json.dump(report, output, indent=2)
    print(json.dumps(report, indent=2))
