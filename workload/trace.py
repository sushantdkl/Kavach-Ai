"""Compile a configuration into an identical offered-request trace for every strategy."""

import hashlib
import json
import random

ENDPOINTS = ("login", "balance", "initiate", "confirm", "transaction")
CLASSES = ("steady", "ramp", "flash", "oscillatory", "sustained_overload", "recovery")
HARD_MAX_RPS = 400


def validate_config(config):
    if not isinstance(config.get("seed"), int) or isinstance(config["seed"], bool):
        raise ValueError("seed must be an integer")  # noqa: TRY004 -- one config error contract
    ceiling = config.get("max_rps")
    if (
        not isinstance(ceiling, int)
        or isinstance(ceiling, bool)
        or not 1 <= ceiling <= HARD_MAX_RPS
    ):
        raise ValueError("max_rps must be an integer in [1, 400]")
    mix = config.get("request_mix", {})
    if (
        set(mix) != set(ENDPOINTS)
        or any(type(v) is not int or v < 0 for v in mix.values())
        or sum(mix.values()) != 100
    ):
        raise ValueError(
            "request_mix must contain all five endpoints with integer weights totaling 100"
        )
    stages = config.get("stages")
    if not isinstance(stages, list) or not stages:
        raise ValueError("nonempty stages required")
    elapsed = 0
    for stage in stages:
        if type(stage.get("duration_s")) is not int or not 1 <= stage["duration_s"] <= 600:
            raise ValueError("stage duration must be 1..600 integer seconds")
        if type(stage.get("rps")) is not int or not 0 <= stage["rps"] <= ceiling:
            raise ValueError("stage RPS exceeds ceiling or is not a nonnegative integer")
        if stage.get("label") not in CLASSES:
            raise ValueError("unknown pattern label")
        elapsed += stage["duration_s"]
    if elapsed != config.get("duration_s") or elapsed > 3600:
        raise ValueError("duration must equal the sum of stages and be <=3600s")
    warmup = config.get("warmup_s", 0)
    if type(warmup) is not int or not 0 <= warmup < elapsed:
        raise ValueError("warmup must be a nonnegative integer smaller than duration")
    return config


def compile_trace(config):
    validate_config(config)
    rng = random.Random(config["seed"])
    rows = []
    elapsed = 0
    weights = [config["request_mix"][name] for name in ENDPOINTS]
    for stage in config["stages"]:
        for second in range(stage["duration_s"]):
            for slot in range(stage["rps"]):
                rows.append(
                    {
                        "sequence": len(rows),
                        "offset_s": elapsed + second + slot / stage["rps"],
                        "endpoint": rng.choices(ENDPOINTS, weights=weights, k=1)[0],
                        "user": rng.randrange(1, 101),
                        "amount_minor": rng.randrange(100, 10001),
                        "label": stage["label"],
                    }
                )
        elapsed += stage["duration_s"]
    return rows


def trace_hash(rows):
    return hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
