from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "frontend" / "src" / "app" / "page.tsx"
CSS = ROOT / "frontend" / "src" / "app" / "globals.css"
INTERACTIONS = ROOT / "frontend" / "src" / "components" / "PremiumInteractions.tsx"


def test_owner_home_keeps_primary_surfaces_and_truthful_money_state():
    source = PAGE.read_text(encoding="utf-8")
    interactions = INTERACTIONS.read_text(encoding="utf-8")
    for label in ("Home", "Pauli", "Work", "World"):
        assert f'label="{label}"' in source
    assert "return 'Unknown'" in source
    assert "Pauli will not invent missing financial data." in source
    assert "Real runtime state only." in source
    assert "Controls that are not backed by the control plane are intentionally not shown." in interactions


def test_final_pauli_visual_identity_is_present_without_fake_runtime_state():
    source = PAGE.read_text(encoding="utf-8")
    styles = CSS.read_text(encoding="utf-8")
    assert "PauliOrb" in source
    assert "pauli-stage" in source
    assert "pauli-orb" in styles
    assert "owner-card" in styles
    assert "prefers-reduced-motion" in styles
    assert "fake chart" not in source.lower()


def test_owner_home_keeps_consequential_action_language():
    source = PAGE.read_text(encoding="utf-8")
    assert "Production, public sends, and consequential spend come back to you." in source
    assert "Approve" in source
    assert "Decline" in source
