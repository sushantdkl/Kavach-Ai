"""Bounded engineering check against a verified loopback payment fixture.

This is not the Locust research workload or a baseline comparison.
"""

import argparse
import hashlib
import ipaddress
import json
import platform
import statistics
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import httpx


def validate_target(url: str) -> str:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "http"
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Use a plain HTTP loopback origin without credentials or path")
    try:
        if not ipaddress.ip_address(parsed.hostname or "").is_loopback:
            raise ValueError("Target must be a literal loopback IP")
    except ValueError as exc:
        raise ValueError("Target must be a literal loopback IP") from exc
    return url.rstrip("/")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default="http://127.0.0.1:8000")
    parser.add_argument("--rps", type=int, default=10, choices=range(1, 21))
    parser.add_argument("--duration", type=int, default=30, choices=range(1, 121))
    parser.add_argument("--output", type=Path, default=Path("docs/evidence"))
    args = parser.parse_args()
    target = validate_target(args.target)
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    folder = args.output / f"smoke-{run_id}"
    folder.mkdir(parents=True, exist_ok=False)
    config = {
        "target": target,
        "rps_ceiling": args.rps,
        "duration_s": args.duration,
        "seed": 240005,
        "purpose": "engineering-smoke-not-research",
    }
    report = {
        "run_id": run_id,
        "config": config,
        "status": "INVALID",
        "config_hash": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest(),
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "working_tree_dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
        ),
        "host": platform.platform(),
        "start_utc": datetime.now(UTC).isoformat(),
    }
    rows = []
    try:
        with httpx.Client(base_url=target, timeout=5, follow_redirects=False, trust_env=False) as c:
            health = c.get("/health")
            health.raise_for_status()
            if health.json() != {
                "status": "ok",
                "service": "kavach-synthetic-payment",
                "synthetic": True,
            }:
                raise RuntimeError("Destination did not identify as the Kavach synthetic fixture")
            # Setup is sequential and paced at the same ceiling as measurement.
            start = time.monotonic()
            r = c.post(
                "/auth/login", json={"username": "synthetic-user-1", "password": "synthetic-only"}
            )
            r.raise_for_status()
            headers = {"Authorization": "Bearer " + r.json()["access_token"]}
            time.sleep(max(0, 1 / args.rps - (time.monotonic() - start)))
            r = c.post(
                "/payments/initiate",
                headers=headers,
                json={
                    "amount_minor": 1200,
                    "recipient": "synthetic-merchant-1",
                    "request_id": "smoke",
                },
            )
            r.raise_for_status()
            receipt = r.json()["transaction_id"]
            time.sleep(1 / args.rps)
            started = time.monotonic()
            previous = started - 1 / args.rps
            for i in range(args.duration * args.rps):
                due = max(started + i / args.rps, previous + 1 / args.rps)
                time.sleep(max(0, due - time.monotonic()))
                if time.monotonic() - started >= args.duration:
                    break  # Never catch up overdue requests in a burst.
                previous = time.monotonic()
                mode = i % 5
                if mode == 0:
                    response = c.post(
                        "/auth/login",
                        json={"username": "synthetic-user-1", "password": "synthetic-only"},
                    )
                elif mode == 1:
                    response = c.get("/wallet/balance", headers=headers)
                elif mode == 2:
                    response = c.post(
                        "/payments/initiate",
                        headers=headers,
                        json={
                            "amount_minor": 1200,
                            "recipient": "synthetic-merchant-1",
                            "request_id": f"smoke-{i}",
                        },
                    )
                elif mode == 3:
                    response = c.post(
                        "/payments/confirm", headers=headers, json={"transaction_id": receipt}
                    )
                else:
                    response = c.get(f"/transactions/{receipt}", headers=headers)
                rows.append(
                    {
                        "sequence": i,
                        "timestamp": datetime.now(UTC).isoformat(),
                        "status": response.status_code,
                        "latency_ms": (time.monotonic() - previous) * 1000,
                    }
                )
            metrics = c.get("/metrics")
            metrics.raise_for_status()
            (folder / "metrics.prom").write_text(metrics.text, encoding="utf-8")
        latencies = sorted(row["latency_ms"] for row in rows)
        errors = sum(row["status"] >= 400 for row in rows)
        report.update(
            requests=len(rows),
            errors=errors,
            mean_latency_ms=statistics.mean(latencies),
            p95_latency_ms=latencies[max(0, int(len(latencies) * 0.95) - 1)],
            elapsed_s=time.monotonic() - started,
            status="PASS"
            if errors == 0 and len(rows) >= 0.95 * args.rps * args.duration
            else "INVALID",
        )
    except Exception as exc:  # noqa: BLE001 -- preserve failed engineering-run evidence
        report["failure"] = f"{type(exc).__name__}: {exc}"
    finally:
        report["end_utc"] = datetime.now(UTC).isoformat()
        (folder / "requests.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )
        (folder / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
