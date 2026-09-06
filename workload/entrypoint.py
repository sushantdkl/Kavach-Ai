"""Hold an isolated load pod for explicit start and artifact export by the runner."""

import json
import os
import subprocess
import time
from pathlib import Path

folder = Path("/data")
folder.mkdir(exist_ok=True)
(folder / "ready.json").write_text(json.dumps({"utc": time.time()}))
deadline = time.monotonic() + 300
while not (folder / "go.json").exists():
    if time.monotonic() > deadline:
        raise SystemExit("Runner did not authorize a workload start within 300 seconds")
    time.sleep(0.1)
start = json.loads((folder / "go.json").read_text())["start_utc"]
os.environ["KAVACH_START_UTC"] = str(start)
duration = json.loads(Path("/config/scenario.json").read_text())["duration_s"]
with (folder / "locust.log").open("w") as log:
    result = subprocess.run(
        [
            "locust",
            "-f",
            "/srv/workload/locustfile.py",
            "--headless",
            "--users",
            "1",
            "--spawn-rate",
            "1",
            "--host",
            f"http://{os.environ['KAVACH_SERVICE_IP']}:8000",
            "--csv",
            "/data/locust",
            "--csv-full-history",
            "--exit-code-on-error",
            "0",
            "--run-time",
            f"{duration + 20}s",
            "--stop-timeout",
            "10",
        ],
        stdout=log,
        stderr=subprocess.STDOUT,
        timeout=duration + 60,
        check=False,
    )
(folder / "exit.json").write_text(json.dumps({"exit_code": result.returncode, "utc": time.time()}))
# Keep artifacts available for kubectl cp. Runner deletes only this named pod after export.
time.sleep(600)
