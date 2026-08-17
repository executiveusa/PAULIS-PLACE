from datetime import datetime, timezone

from api import health


def test_event_timestamp_parsing_accepts_z_and_invalid():
    parsed = health._event_ts({"ts": "2026-08-11T06:30:00Z"})
    assert parsed == datetime(2026, 8, 11, 6, 30, tzinfo=timezone.utc)
    assert health._event_ts({"ts": "not-a-date"}) < parsed


def test_target_agent_prefers_explicit_target_avatar():
    env = {
        "worker_profile": "judge",
        "body": {"target_avatar": "builder"},
    }
    assert health._target_agent(env) == "builder"


def test_target_agent_maps_runtime_profiles_to_world_agents():
    assert health._target_agent({"worker_profile": "score", "body": {}}) == "critic"
    assert health._target_agent({"worker_profile": "judge", "body": {}}) == "guardian"
    assert health._target_agent({"worker_profile": "write_short", "body": {}}) == "builder"


def test_recent_envelopes_are_sorted_by_event_timestamp(monkeypatch, tmp_path):
    day = tmp_path / "2026-08-11"
    day.mkdir()
    (day / "evt_random-a.json").write_text(
        '{"event_id":"evt-a","ts":"2026-08-11T06:00:00Z","worker_profile":"builder","body":{}}',
        encoding="utf-8",
    )
    (day / "evt_random-z.json").write_text(
        '{"event_id":"evt-z","ts":"2026-08-11T05:00:00Z","worker_profile":"builder","body":{}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(health, "_ops_root", lambda: tmp_path)

    events = health._recent_envelopes(2)
    assert [event["event_id"] for event in events] == ["evt-a", "evt-z"]
