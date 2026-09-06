"""Read the container's own cgroup v2 counters at scrape time, without caching."""

import time
from pathlib import Path

from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily


class CgroupCollector:
    def __init__(self, root: Path = Path("/sys/fs/cgroup")):
        self.root = root

    def collect(self):
        try:
            cpu = dict(line.split() for line in (self.root / "cpu.stat").read_text().splitlines())
            memory = int((self.root / "memory.current").read_text())
            stats = dict(
                line.split() for line in (self.root / "memory.stat").read_text().splitlines()
            )
            working_set = max(0, memory - int(stats.get("inactive_file", "0")))
            usage = int(cpu["usage_usec"]) / 1_000_000
        except (OSError, ValueError, KeyError):
            return  # Unsupported host is missing telemetry, never fabricated zero.
        yield CounterMetricFamily(
            "kavach_container_cpu_seconds", "Own cgroup v2 cumulative CPU seconds", value=usage
        )
        yield GaugeMetricFamily(
            "kavach_container_memory_working_set_bytes",
            "Own cgroup memory.current minus inactive_file",
            value=working_set,
        )
        yield GaugeMetricFamily(
            "kavach_container_sample_timestamp_seconds",
            "UTC time of cgroup read",
            value=time.time(),
        )
