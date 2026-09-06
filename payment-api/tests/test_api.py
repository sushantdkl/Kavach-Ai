import pytest
from app.main import Settings, create_app
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families


def client(**kwargs):
    return TestClient(create_app(Settings(cpu_work_factor=5, io_delay_ms=0, **kwargs)))


def auth(c, user="synthetic-user-1"):
    r = c.post("/auth/login", json={"username": user, "password": "synthetic-only"})
    assert r.status_code == 200
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def payment(c, headers):
    return c.post(
        "/payments/initiate",
        headers=headers,
        json={"amount_minor": 1200, "recipient": "synthetic-merchant-1", "request_id": "request-1"},
    )


def test_complete_flow_across_replicas():
    first, second = client(), client()
    headers = auth(first)
    assert second.get("/wallet/balance", headers=headers).json()["currency"] == "TEST"
    receipt = payment(first, headers).json()["transaction_id"]
    assert payment(second, headers).json()["transaction_id"] == receipt
    for _ in range(2):
        r = second.post("/payments/confirm", headers=headers, json={"transaction_id": receipt})
        assert r.status_code == 200
        assert r.json()["status"] == "confirmed"
    assert first.get(f"/transactions/{receipt}", headers=headers).status_code == 200


def test_auth_ownership_and_tampering():
    c = client()
    assert c.get("/wallet/balance").status_code == 401
    headers = auth(c)
    receipt = payment(c, headers).json()["transaction_id"]
    other = auth(c, "synthetic-user-2")
    assert c.get(f"/transactions/{receipt}", headers=other).status_code == 403
    assert c.get(f"/transactions/{receipt}x", headers=headers).status_code == 401
    assert c.post("/auth/login", json={"username": "real-user", "password": "x"}).status_code == 422


@pytest.mark.parametrize("amount", [0, -1, 1_000_001, 1.5, True, "1200"])
def test_amount_validation(amount):
    c = client()
    assert (
        c.post(
            "/payments/initiate",
            headers=auth(c),
            json={"amount_minor": amount, "recipient": "synthetic-merchant-1", "request_id": "a"},
        ).status_code
        == 422
    )


def test_metrics_count_status_and_template_without_probe_pollution():
    c = client()
    headers = auth(c)
    receipt = payment(c, headers).json()["transaction_id"]
    c.get(f"/transactions/{receipt}", headers=headers)
    c.get("/wallet/balance")
    c.get("/health")
    text = c.get("/metrics").text
    samples = [s for f in text_string_to_metric_families(text) for s in f.samples]
    counts = [s for s in samples if s.name == "kavach_requests_total"]
    assert sum(s.value for s in counts) == 4
    assert any(s.labels["status"] == "401" for s in counts)
    assert any(s.labels["route"] == "/transactions/{id}" for s in counts)
    assert receipt not in text
    assert next(s.value for s in samples if s.name == "kavach_in_flight_requests") == 0
    assert 'le="0.3"' in text


def test_errors_are_deterministic_and_health_remains_healthy():
    c = client(error_injection_rate=1)
    for _ in range(2):
        assert (
            c.post(
                "/auth/login", json={"username": "synthetic-user-1", "password": "synthetic-only"}
            ).status_code
            == 503
        )
    assert c.get("/health").status_code == 200
    assert 'status="503"} 2.0' in c.get("/metrics").text


@pytest.mark.parametrize(
    "kwargs",
    [
        {"cpu_work_factor": -1},
        {"io_delay_ms": float("nan")},
        {"error_injection_rate": 1.1},
        {"signing_key": "short"},
    ],
)
def test_settings_reject_invalid_experiment_knobs(kwargs):
    with pytest.raises(ValueError):
        Settings(**kwargs)


def test_db_flag_cannot_silently_change_scientific_design(monkeypatch):
    monkeypatch.setenv("KAVACH_DB_ENABLED", "true")
    with pytest.raises(ValueError, match="not implemented"):
        Settings.from_env()
