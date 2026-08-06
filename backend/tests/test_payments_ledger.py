"""Tests for spec §06 ledger service + payments."""
import sys
from pathlib import Path
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))


def test_ledger_entry_model_tables_present():
    from services.ledger_service import LedgerEntry
    assert LedgerEntry.__tablename__ == "yappy_ledger"
    cols = {c.name for c in LedgerEntry.__table__.columns}
    for c in ["entry_id", "kind", "debit_account", "credit_account",
              "amount_usd", "payment_id", "envelope_ref"]:
        assert c in cols, f"missing ledger column {c}"


def test_ledger_write_function_signature():
    from services.ledger_service import write_ledger_entry
    import inspect
    sig = inspect.signature(write_ledger_entry)
    required = {"entry_id", "kind", "debit_account", "credit_account", "amount_usd"}
    assert required.issubset(sig.parameters.keys())


def test_reconcile_event_signature():
    from services.ledger_service import reconcile_event
    import inspect
    sig = inspect.signature(reconcile_event)
    required = {"payment_id", "provider", "amount_usd"}
    assert required.issubset(sig.parameters.keys())


def test_payments_api_creem_webhook_endpoint_present():
    from api import payments as p
    # The FastAPI router exposes route paths in .paths
    paths = [r.path for r in p.router.routes]
    assert any("creem" in path for path in paths)
    assert any("btcpay" in path for path in paths)