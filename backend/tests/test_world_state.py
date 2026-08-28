from datetime import datetime, timezone

from api import health


def test_event_timestamp_parsing_accepts_z_and_invalid():
    parsed = health._event_ts({"ts": "2026-08-11T06:30:00Z"})
    assert parsed == datetime(2026, 8, 11, 6, 30, tzinfo=timezone.utc)
    assert health._event_ts({"ts": "not-a-date"}) < parsed


def test_target_agent_prefers_explicit_target_avatar():
    env = {"worker_profile": "judge", "body": {"target_avatar": "builder"}}
    assert health._target_agent(env) == "builder"


def test_target_agent_maps_runtime_profiles_to_world_agents():
    assert health._target_agent({"worker_profile": "score", "body": {}}) == "critic"
    assert health._target_agent({"worker_profile": "judge", "body": {}}) == "guardian"
    assert health._target_agent({"worker_profile": "write_short", "body": {}}) == "builder"


def test_recent_envelopes_are_sorted_by_event_timestamp(monkeypatch, tmp_path):
    day = tmp_path / "2026-08-11"
    day.mkdir()
    (day / "evt_random-a.json").write_text('{"event_id":"evt-a","ts":"2026-08-11T06:00:00Z","worker_profile":"builder","body":{}}', encoding="utf-8")
    (day / "evt_random-z.json").write_text('{"event_id":"evt-z","ts":"2026-08-11T05:00:00Z","worker_profile":"builder","body":{}}', encoding="utf-8")
    monkeypatch.setattr(health, "_ops_root", lambda: tmp_path)
    events = health._recent_envelopes(2)
    assert [event["event_id"] for event in events] == ["evt-a", "evt-z"]


def test_normalize_position_accepts_xyz_and_falls_back_deterministically():
    assert health._normalize_position({"x": 1, "y": 2.5, "z": -3}, 0) == [1.0, 2.5, -3.0]
    assert health._normalize_position([4, 0, 5], 0) == [4.0, 0.0, 5.0]
    assert health._normalize_position({"x": "bad", "y": 0, "z": 0}, 1) == health.DEFAULT_POSITIONS[1]


def test_avatar_projection_uses_agent_key_and_canonical_presence():
    row = {
        "database_id": "b4518106-766d-4e88-964b-8dbb75973faf",
        "agent_key": "guardian",
        "name": "Guardian",
        "role": "Safety & policy",
        "agent_status": "idle",
        "presence_state": "working",
        "position": {"x": 2, "y": 0, "z": 4},
        "activity_summary": "Reviewing evidence",
        "presence_updated_at": datetime(2026, 8, 28, 18, 0, tzinfo=timezone.utc),
        "location_key": "guardian-office",
        "location_name": "Guardian Office",
        "mission_id": "d86a272d-f699-4cf4-8aad-e6702caf5f27",
        "mission_title": "Verify release",
        "mission_status": "VERIFYING",
        "model_key": "judge-model",
    }
    avatar = health._avatar_from_row(row, 0)
    assert avatar["id"] == "guardian"
    assert avatar["database_id"] == row["database_id"]
    assert avatar["state"] == "working"
    assert avatar["position"] == [2.0, 0.0, 4.0]
    assert avatar["model"] == "judge-model"
    assert avatar["location"]["key"] == "guardian-office"
    assert avatar["mission"]["status"] == "VERIFYING"
    assert avatar["last_event_at"] == "2026-08-28T18:00:00+00:00"
