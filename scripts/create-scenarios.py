"""Create initial development traces; existing configs are never replaced."""

from pathlib import Path

import yaml

MIX = {"login": 10, "balance": 30, "initiate": 30, "confirm": 20, "transaction": 10}
SHAPES = {
    "steady": [(180, 40, "steady")],
    "ramp": [(30, rate, "ramp") for rate in (20, 40, 60, 80, 100, 120)],
    "flash": [(45, 20, "steady"), (45, 180, "flash"), (90, 20, "recovery")],
    "repeated_burst": [(15, rate, "flash" if rate > 20 else "steady") for rate in [20, 150] * 6],
    "oscillatory": [(15, rate, "oscillatory") for rate in [10, 180] * 6],
    "sustained_overload": [(180, 300, "sustained_overload")],
    "hybrid": [
        (30, 30, "steady"),
        (30, 80, "ramp"),
        (30, 200, "flash"),
        (30, 20, "recovery"),
        (30, 200, "oscillatory"),
        (30, 30, "recovery"),
    ],
    "recovery": [(60, 180, "sustained_overload"), (120, 10, "recovery")],
}


def write(name, stages, warmup, root):
    cfg = {
        "name": name,
        "seed": 240005,
        "max_rps": 400,
        "duration_s": sum(s[0] for s in stages),
        "warmup_s": warmup,
        "request_mix": MIX,
        "stages": [
            {"duration_s": duration, "rps": rps, "label": label} for duration, rps, label in stages
        ],
    }
    root.mkdir(parents=True, exist_ok=True)
    with (root / f"{name}.yaml").open("x", encoding="utf-8") as output:
        yaml.safe_dump(cfg, output, sort_keys=False)


if __name__ == "__main__":
    for name, shape in SHAPES.items():
        write(name, [(30, 10, "steady"), *shape], 30, Path("workload/scenarios"))
    write("smoke", [(60, 10, "steady")], 20, Path("experiments/configs"))
    write(
        "capacity",
        [
            (30, 10, "steady"),
            *[(60, rps, "ramp") for rps in (20, 40, 80, 120, 180, 240)],
            (60, 10, "recovery"),
        ],
        30,
        Path("experiments/configs"),
    )
