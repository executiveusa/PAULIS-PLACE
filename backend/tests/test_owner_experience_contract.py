def test_owner_home_does_not_restore_synthetic_financial_zeros():
    with open("supabase/functions/pauli-control/index.ts", "r", encoding="utf-8") as handle:
        edge = handle.read()
    assert "owner_briefs" in edge
    assert 'revenue_cents: null' in edge
    assert 'profit_cents: null' in edge
    assert "treasury_entries" not in edge
    assert "coalesce(sum" not in edge


def test_owner_home_uses_four_primary_surfaces_and_truthful_money():
    with open("frontend/src/app/page.tsx", "r", encoding="utf-8") as handle:
        source = handle.read()
    for label in ("Home", "Pauli", "Work", "World", "Needs You", "Working Now"):
        assert label in source
    assert "Unknown" in source
    assert "coverageText" in source
    assert "System truth" not in source
    assert "Revenue today" not in source


def test_control_types_require_source_qualified_owner_brief():
    with open("frontend/src/lib/pauliControl.ts", "r", encoding="utf-8") as handle:
        source = handle.read()
    assert "export interface OwnerBrief" in source
    assert "coverage_status" in source
    assert "revenue_cents: number | null" in source
    assert "owner_brief: OwnerBrief" in source
