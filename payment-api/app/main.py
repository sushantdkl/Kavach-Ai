"""Synthetic, replica-independent payment fixture. No actual payment occurs."""

import asyncio
import base64
import hashlib
import hmac
import json
import math
import os
import time
from dataclasses import dataclass
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Response
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest
from prometheus_client.exposition import CONTENT_TYPE_LATEST
from pydantic import BaseModel, Field

from app.resources import CgroupCollector


@dataclass(frozen=True)
class Settings:
    cpu_work_factor: int = 2000
    io_delay_ms: float = 2.0
    error_injection_rate: float = 0.0
    seed: int = 240005
    signing_key: str = "kavach-local-synthetic-fixture-v1"

    def __post_init__(self):
        if not 0 <= self.cpu_work_factor <= 1_000_000:
            raise ValueError("CPU work factor must be in [0, 1000000]")
        if not math.isfinite(self.io_delay_ms) or not 0 <= self.io_delay_ms <= 1000:
            raise ValueError("IO delay must be finite and in [0, 1000] ms")
        if not math.isfinite(self.error_injection_rate) or not 0 <= self.error_injection_rate <= 1:
            raise ValueError("Error injection rate must be in [0, 1]")
        if len(self.signing_key) < 16:
            raise ValueError("Fixture signing key must be at least 16 characters")

    @classmethod
    def from_env(cls):
        if os.getenv("KAVACH_DB_ENABLED", "false").lower() not in {"false", "0"}:
            raise ValueError("Database mode is not implemented; use the stateless fixture")
        return cls(
            cpu_work_factor=int(os.getenv("KAVACH_CPU_WORK_FACTOR", "2000")),
            io_delay_ms=float(os.getenv("KAVACH_IO_DELAY_MS", "2")),
            error_injection_rate=float(os.getenv("KAVACH_ERROR_INJECTION_RATE", "0")),
            seed=int(os.getenv("KAVACH_SEED", "240005")),
            signing_key=os.getenv("KAVACH_SIGNING_KEY", cls.signing_key),
        )


class Login(BaseModel):
    username: str = Field(pattern=r"^synthetic-user-[0-9]{1,4}$")
    password: str = Field(max_length=100)


class Payment(BaseModel):
    amount_minor: int = Field(strict=True, gt=0, le=1_000_000)
    recipient: str = Field(pattern=r"^synthetic-merchant-[0-9]{1,4}$")
    request_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")


class Confirmation(BaseModel):
    transaction_id: str = Field(min_length=10, max_length=2048)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(title="Kavach synthetic payment fixture", version="0.1.0")
    registry = CollectorRegistry()
    registry.register(CgroupCollector())
    requests = Counter(
        "kavach_requests_total",
        "Completed business requests",
        ["method", "route", "status"],
        registry=registry,
    )
    durations = Histogram(
        "kavach_request_duration_seconds",
        "Business request latency",
        ["method", "route"],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 1, 2, 5, 10),
        registry=registry,
    )
    inflight = Gauge(
        "kavach_in_flight_requests", "Business requests in progress", registry=registry
    )
    app.state.registry = registry
    app.state.settings = settings

    def sign(payload: dict, kind: str) -> str:
        raw = json.dumps({"kind": kind, **payload}, sort_keys=True, separators=(",", ":")).encode()
        encoded = base64.urlsafe_b64encode(raw).decode().rstrip("=")
        signature = hmac.new(
            settings.signing_key.encode(), encoded.encode(), hashlib.sha256
        ).hexdigest()
        return f"{encoded}.{signature}"

    def verify(token: str, kind: str) -> dict:
        try:
            encoded, signature = token.split(".")
            expected = hmac.new(
                settings.signing_key.encode(), encoded.encode(), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise ValueError("signature")
            payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
            if payload["kind"] != kind:
                raise ValueError("kind")
            return payload
        except (ValueError, KeyError, TypeError, UnicodeError) as exc:
            raise HTTPException(401, "Invalid synthetic fixture token") from exc

    def identity(authorization: str | None) -> str:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "Synthetic bearer token required")
        return verify(authorization[7:], "session")["user"]

    async def work(key: str):
        # Fixed iterations, not a wall-clock busy wait. Same request/seed => same work.
        digest = hashlib.sha256(f"{settings.seed}:{key}".encode()).digest()
        failure_draw = int.from_bytes(digest[:8], "big") / 2**64
        for _ in range(settings.cpu_work_factor):
            digest = hashlib.sha256(digest).digest()
        await asyncio.sleep(settings.io_delay_ms / 1000)
        if failure_draw < settings.error_injection_rate:
            raise HTTPException(503, "Deterministic synthetic injected error")

    @app.middleware("http")
    async def instrument(request, call_next):
        if request.url.path in {"/health", "/metrics"}:
            return await call_next(request)
        start = time.perf_counter()
        status = 500
        inflight.inc()
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            route = getattr(request.scope.get("route"), "path", "unmatched")
            requests.labels(request.method, route, str(status)).inc()
            durations.labels(request.method, route).observe(time.perf_counter() - start)
            inflight.dec()

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "kavach-synthetic-payment", "synthetic": True}

    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        return Response(generate_latest(registry), headers={"Content-Type": CONTENT_TYPE_LATEST})

    @app.post("/auth/login")
    async def login(body: Login):
        if body.password != "synthetic-only":
            raise HTTPException(401, "Use the documented synthetic fixture password")
        await work(f"login:{body.username}")
        return {
            "access_token": sign({"user": body.username}, "session"),
            "token_type": "bearer",
            "synthetic": True,
        }

    @app.get("/wallet/balance")
    async def balance(authorization: Annotated[str | None, Header()] = None):
        user = identity(authorization)
        await work(f"balance:{user}")
        return {"user": user, "balance_minor": 1_000_000, "currency": "TEST", "synthetic": True}

    @app.post("/payments/initiate")
    async def initiate(body: Payment, authorization: Annotated[str | None, Header()] = None):
        user = identity(authorization)
        await work(f"initiate:{user}:{body.request_id}")
        receipt = sign({"user": user, **body.model_dump()}, "transaction")
        return {"transaction_id": receipt, "status": "initiated", "synthetic": True}

    @app.post("/payments/confirm")
    async def confirm(body: Confirmation, authorization: Annotated[str | None, Header()] = None):
        user = identity(authorization)
        receipt = verify(body.transaction_id, "transaction")
        if receipt["user"] != user:
            raise HTTPException(403, "Receipt belongs to another synthetic user")
        await work(f"confirm:{body.transaction_id}")
        return {
            "transaction_id": body.transaction_id,
            "status": "confirmed",
            "synthetic": True,
            "state_persisted": False,
        }

    @app.get("/transactions/{id}")
    async def transaction(id: str, authorization: Annotated[str | None, Header()] = None):
        user = identity(authorization)
        if len(id) > 2048:
            raise HTTPException(422, "Receipt too long")
        receipt = verify(id, "transaction")
        if receipt["user"] != user:
            raise HTTPException(403, "Receipt belongs to another synthetic user")
        await work(f"transaction:{id}")
        return {
            **receipt,
            "transaction_id": id,
            "status": "synthetic_receipt",
            "synthetic": True,
            "state_persisted": False,
        }

    return app


app = create_app()
