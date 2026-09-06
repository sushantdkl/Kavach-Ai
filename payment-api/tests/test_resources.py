from app.resources import CgroupCollector


def test_cgroup_counter_units_and_working_set(tmp_path):
    (tmp_path / "cpu.stat").write_text(
        "usage_usec 2500000\nuser_usec 2000000\nsystem_usec 500000\n"
    )
    (tmp_path / "memory.current").write_text("4096")
    (tmp_path / "memory.stat").write_text("inactive_file 1024\nanon 3072\n")
    metrics = {m.name: m.samples[0].value for m in CgroupCollector(tmp_path).collect()}
    assert metrics["kavach_container_cpu_seconds"] == 2.5
    assert metrics["kavach_container_memory_working_set_bytes"] == 3072
    assert metrics["kavach_container_sample_timestamp_seconds"] > 0


def test_absent_cgroup_never_fabricates_zero(tmp_path):
    assert list(CgroupCollector(tmp_path).collect()) == []
