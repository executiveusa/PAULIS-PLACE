from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "frontend" / "src" / "app" / "page.tsx"
SIDEBAR = ROOT / "frontend" / "src" / "components" / "Sidebar.tsx"
INTERACTIONS = ROOT / "frontend" / "src" / "components" / "PremiumInteractions.tsx"
CSS = ROOT / "frontend" / "src" / "app" / "premium-interactions.css"


def test_owner_home_is_not_wrapped_in_technical_sidebar():
    source = SIDEBAR.read_text(encoding="utf-8")
    assert "if (pathname === '/') return null" in source


def test_owner_actions_have_lifecycle_feedback():
    source = PAGE.read_text(encoding="utf-8")
    assert "Starting mission…" in source
    assert "Mission started" in source
    assert "Decision was not recorded" in source
    assert "Sign-in link sent" in source
    assert "FeedbackStack" in source


def test_agent_detail_is_real_state_only_and_gesture_driven():
    source = INTERACTIONS.read_text(encoding="utf-8")
    assert "drag={reduceMotion ? false : 'y'}" in source
    assert "last_heartbeat_at" in source
    assert "world_location_key" in source
    assert "Controls that are not backed by the control plane are intentionally not shown." in source
    assert "Open workforce control" in source


def test_apple_accessibility_fallbacks_are_present():
    source = CSS.read_text(encoding="utf-8")
    assert "prefers-reduced-transparency" in source
    assert "prefers-contrast: more" in source
    assert "prefers-reduced-motion" in source
    assert ".pressable:active" in source
