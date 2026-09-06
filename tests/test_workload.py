import copy
from itertools import pairwise

import pytest

from workload.trace import compile_trace, trace_hash, validate_config


def fixture():
    return {
        "name": "test",
        "seed": 240005,
        "max_rps": 20,
        "duration_s": 4,
        "warmup_s": 0,
        "request_mix": {
            "login": 10,
            "balance": 30,
            "initiate": 30,
            "confirm": 20,
            "transaction": 10,
        },
        "stages": [
            {"rps": 5, "duration_s": 2, "label": "steady"},
            {"rps": 20, "duration_s": 2, "label": "flash"},
        ],
    }


def test_same_seed_identical_offered_trace():
    config = fixture()
    assert compile_trace(config) == compile_trace(config)
    assert len(compile_trace(config)) == 50
    other = copy.deepcopy(config)
    other["seed"] += 1
    assert trace_hash(compile_trace(config)) != trace_hash(compile_trace(other))
    assert [r["offset_s"] for r in compile_trace(config)] == [
        r["offset_s"] for r in compile_trace(other)
    ]


def test_trace_does_not_exceed_ceiling_or_duration():
    config = fixture()
    trace = compile_trace(config)
    assert trace[-1]["offset_s"] < config["duration_s"]
    assert all(
        b["offset_s"] - a["offset_s"] >= 1 / config["max_rps"] - 1e-10 for a, b in pairwise(trace)
    )


@pytest.mark.parametrize(
    "field,value", [("max_rps", 401), ("duration_s", 5), ("seed", "1"), ("warmup_s", 4)]
)
def test_invalid_configs(field, value):
    config = fixture()
    config[field] = value
    with pytest.raises(ValueError):
        validate_config(config)


def test_stage_cannot_exceed_ceiling():
    config = fixture()
    config["stages"][0]["rps"] = 21
    with pytest.raises(ValueError):
        validate_config(config)
