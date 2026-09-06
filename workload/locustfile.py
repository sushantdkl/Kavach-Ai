"""One dispatcher, bounded concurrent synthetic HTTP requests; no distributed mode."""

import base64
import hashlib
import hmac
import ipaddress
import json
import os
import socket
import time
from pathlib import Path

import gevent
import requests
from gevent.pool import Group
from locust import HttpUser, task
from locust.exception import StopUser

from workload.trace import compile_trace, trace_hash, validate_config

SERVICE = "payment-api.kavach-lab.svc.cluster.local"


def signed(payload, kind):
    raw = json.dumps({"kind": kind, **payload}, sort_keys=True, separators=(",", ":")).encode()
    encoded = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    signature = hmac.new(
        b"kavach-local-synthetic-fixture-v1", encoded.encode(), hashlib.sha256
    ).hexdigest()
    return f"{encoded}.{signature}"


class TraceReplay(HttpUser):
    fixed_count = 1

    def on_start(self):
        expected = os.environ["KAVACH_SERVICE_IP"]
        if not any(
            ipaddress.ip_address(expected) in ipaddress.ip_network(network)
            for network in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
        ):
            raise RuntimeError("Target is not an RFC1918 test Service")
        resolved = {
            item[4][0] for item in socket.getaddrinfo(SERVICE, 8000, type=socket.SOCK_STREAM)
        }
        if resolved != {expected} or self.host != f"http://{expected}:8000":
            raise RuntimeError("Service DNS and verified cluster Service IP disagree")
        self.client.trust_env = False
        self.client.headers.update({"Connection": "close"})
        with requests.Session() as probe:
            probe.trust_env = False
            response = probe.get(self.host + "/health", timeout=5, allow_redirects=False)
            if (
                response.status_code != 200
                or response.json().get("service") != "kavach-synthetic-payment"
            ):
                raise RuntimeError("Destination is not the synthetic fixture")
        self.config = validate_config(json.loads(Path("/config/scenario.json").read_text()))
        self.trace = compile_trace(self.config)
        self.group = Group()

    def issue(self, event, output, started, lag):
        user = f"synthetic-user-{event['user']}"
        headers = {"Authorization": "Bearer " + signed({"user": user}, "session")}
        payload = {
            "amount_minor": event["amount_minor"],
            "recipient": "synthetic-merchant-1",
            "request_id": f"trace-{event['sequence']}",
        }
        receipt = signed({"user": user, **payload}, "transaction")
        endpoint = event["endpoint"]
        kwargs = {"headers": headers, "timeout": 5, "allow_redirects": False}
        if endpoint == "login":
            method, path = "POST", "/auth/login"
            kwargs["json"] = {"username": user, "password": "synthetic-only"}
        elif endpoint == "balance":
            method, path = "GET", "/wallet/balance"
        elif endpoint == "initiate":
            method, path = "POST", "/payments/initiate"
            kwargs["json"] = payload
        elif endpoint == "confirm":
            method, path = "POST", "/payments/confirm"
            kwargs["json"] = {"transaction_id": receipt}
        else:
            method, path = "GET", f"/transactions/{receipt}"
        begin = time.monotonic()
        response = self.client.request(
            method, path, name="/transactions/{id}" if endpoint == "transaction" else path, **kwargs
        )
        output.write(
            json.dumps(
                {
                    **event,
                    "scheduled_utc": started + event["offset_s"],
                    "dispatched_utc": time.time() - (time.monotonic() - begin),
                    "completed_utc": time.time(),
                    "generator_lag_s": lag,
                    "status": response.status_code,
                    "latency_ms": (time.monotonic() - begin) * 1000,
                    "dropped": False,
                }
            )
            + "\n"
        )
        output.flush()

    @task
    def replay(self):
        started = float(os.environ["KAVACH_START_UTC"])
        origin = time.monotonic() + (started - time.time())
        dropped = 0
        previous = -float("inf")
        with Path("/data/requests.jsonl").open("x") as output:
            for event in self.trace:
                due = origin + event["offset_s"]
                gevent.sleep(
                    max(
                        0,
                        due - time.monotonic(),
                        previous + 1 / self.config["max_rps"] - time.monotonic(),
                    )
                )
                now = time.monotonic()
                lag = now - due
                if lag > 0.1 or len(self.group) >= 200:
                    dropped += 1
                    output.write(
                        json.dumps(
                            {
                                **event,
                                "scheduled_utc": started + event["offset_s"],
                                "generator_lag_s": lag,
                                "dropped": True,
                            }
                        )
                        + "\n"
                    )
                    continue
                previous = now
                self.group.spawn(self.issue, event, output, started, lag)
            self.group.join(timeout=10, raise_error=True)
        Path("/data/replay.json").write_text(
            json.dumps(
                {
                    "trace_hash": trace_hash(self.trace),
                    "offered": len(self.trace),
                    "dropped": dropped,
                    "start_utc": started,
                    "end_utc": time.time(),
                    "generator_valid": dropped == 0 and not self.group,
                    "request_rate_ceiling": self.config["max_rps"],
                },
                indent=2,
            )
        )
        gevent.spawn(self.environment.runner.quit)
        raise StopUser()
