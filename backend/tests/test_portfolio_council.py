from pathlib import Path

from agents import portfolio_council


def test_portfolio_council_has_all_required_independent_roles():
    roles = [role for role, _, _ in portfolio_council.ROLE_PROFILES]
    assert roles == [
        "operator",
        "cfo",
        "consolidator",
        "red_team",
        "evidence_judge",
        "mission_guardian",
        "opportunity_advocate",
    ]
    assert len(set(roles)) == 7


def test_parse_json_accepts_fenced_payload():
    parsed = portfolio_council._parse_json('```json\n{"position":"TEST"}\n```')
    assert parsed["position"] == "TEST"


def test_recent_deliberations_is_empty_when_store_missing(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(portfolio_council, "_decision_root", lambda: tmp_path / "missing")
    assert portfolio_council.recent_deliberations(10) == []


def test_recent_deliberations_orders_by_timestamp(monkeypatch, tmp_path: Path):
    root = tmp_path / "portfolio-decisions"
    day = root / "2026-08-11"
    day.mkdir(parents=True)
    (day / "older.json").write_text('{"decision_id":"old","ts":"2026-08-11T01:00:00Z"}', encoding="utf-8")
    (day / "newer.json").write_text('{"decision_id":"new","ts":"2026-08-11T02:00:00Z"}', encoding="utf-8")
    monkeypatch.setattr(portfolio_council, "_decision_root", lambda: root)
    results = portfolio_council.recent_deliberations(10)
    assert [item["decision_id"] for item in results] == ["new", "old"]
