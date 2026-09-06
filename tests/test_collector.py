import copy

import pytest

from collector.collect import REQUIRED, validate_rows


def good_row():
    row = dict.fromkeys(REQUIRED, 0)
    row.update(
        timestamp=100,
        app_source_timestamp=99,
        cpu_source_timestamp=99,
        memory_source_timestamp=99,
        ready_replicas=1,
        desired_replicas=1,
        app_targets_up=1,
        app_targets_count=1,
        cadvisor_up=1,
        snapshot_duration_s=0.1,
    )
    return row


def test_idle_latency_may_be_null():
    assert validate_rows([good_row()], 1, 2)["status"] == "PASS"


@pytest.mark.parametrize("field", REQUIRED)
def test_missing_required_stream_invalidates(field):
    row = good_row()
    row[field] = None
    assert validate_rows([row], 1, 2)["status"] == "INVALID"


def test_stale_timestamp_and_missing_latency():
    row = good_row()
    row.update(cpu_source_timestamp=90, current_rps=10)
    reasons = validate_rows([row], 1, 2)["reasons"]
    assert any("stale" in reason for reason in reasons)
    assert any("missing_latency" in reason for reason in reasons)


def test_nan_gap_and_partial_scrapes_fail():
    row = good_row()
    second = copy.copy(row)
    second.update(timestamp=104, cpu_usage_cores=float("nan"), app_targets_count=2)
    result = validate_rows([row, second], 2, 2)
    assert any("cadence_gap" in reason for reason in result["reasons"])
    assert any("incomplete_app" in reason for reason in result["reasons"])
    assert any("cpu_usage_cores" in reason for reason in result["reasons"])
