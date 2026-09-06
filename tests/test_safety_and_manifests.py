from pathlib import Path

import pytest
import yaml

from scripts.smoke import validate_target


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "http://192.168.1.1",
        "https://127.0.0.1",
        "http://localhost",
        "http://127.0.0.1@evil.com",
        "http://127.0.0.1/path",
        "http://127.0.0.1?target=evil",
        "http://127.0.0.1#x",
    ],
)
def test_smoke_rejects_non_testbed_targets(url):
    with pytest.raises(ValueError):
        validate_target(url)


def test_loopback_literal():
    assert validate_target("http://127.0.0.1:8000/") == "http://127.0.0.1:8000"
    assert validate_target("http://[::1]:8000") == "http://[::1]:8000"


def test_deployment_is_local_single_worker_with_resource_limits():
    deployment = yaml.safe_load(Path("infrastructure/k8s/base/deployment.yaml").read_text())
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    assert container["imagePullPolicy"] == "Never"
    assert container["resources"]["requests"]["cpu"] == "250m"
    for probe in ("startupProbe", "readinessProbe", "livenessProbe"):
        assert container[probe]["httpGet"]["path"] == "/health"
    service = yaml.safe_load(Path("infrastructure/k8s/base/service.yaml").read_text())
    assert service["spec"]["type"] == "ClusterIP"
