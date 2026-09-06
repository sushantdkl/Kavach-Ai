import json

import yaml

from experiments.calibration import summarize
from workload.trace import compile_trace, validate_config


def test_all_shipped_scenarios_have_identical_trace_replay():
    from pathlib import Path

    paths = list(Path("workload/scenarios").glob("*.yaml"))
    assert len(paths) == 8
    for path in paths:
        config = validate_config(yaml.safe_load(path.read_text()))
        first = compile_trace(config)
        assert first == compile_trace(config)
        assert first[-1]["offset_s"] < config["duration_s"]


def test_capacity_reports_keep_invalid_status_and_exclude_step_settling(tmp_path):
    (tmp_path / "validation.json").write_text(json.dumps({"status": "INVALID"}))
    (tmp_path / "config.yaml").write_text(
        yaml.safe_dump({"workload": {"stages": [{"duration_s": 20, "rps": 1}]}})
    )
    (tmp_path / "locust").mkdir()
    rows = [
        {"offset_s": i, "dropped": False, "latency_ms": 999 if i < 10 else 20, "status": 200}
        for i in range(20)
    ]
    (tmp_path / "locust/requests.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    report = summarize(tmp_path)
    assert report["validity"] == "INVALID"
    assert report["parameters_frozen"] is False
    assert report["stages"][0]["offered"] == 10
    assert report["stages"][0]["p95_latency_ms"] == 20
