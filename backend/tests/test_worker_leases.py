from types import SimpleNamespace

from services.worker_leases import WorkerLease, acquire_task_lease, heartbeat_task_lease, release_task_lease


class MappingResult:
    def __init__(self, row):
        self._row = row

    def mappings(self):
        return self

    def first(self):
        return self._row


class RowcountResult:
    def __init__(self, rowcount=1):
        self.rowcount = rowcount


class FakeDb:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def execute(self, statement, params=None):
        self.calls.append((str(statement), params or {}))
        return self.results.pop(0)


def test_acquire_task_lease_returns_durable_identity():
    row = {
        "id": "11111111-1111-1111-1111-111111111111",
        "task_id": "22222222-2222-2222-2222-222222222222",
        "worker_key": "worker-a",
        "lease_token": "33333333-3333-3333-3333-333333333333",
        "expires_at": "later",
    }
    db = FakeDb([MappingResult(row)])

    lease = acquire_task_lease(
        db,
        row["task_id"],
        "44444444-4444-4444-4444-444444444444",
        worker_key="worker-a",
        lease_seconds=90,
    )

    assert isinstance(lease, WorkerLease)
    assert lease.worker_key == "worker-a"
    assert lease.task_id == row["task_id"]
    assert "pauli.worker_leases" in db.calls[0][0]
    assert db.calls[0][1]["seconds"] == 90


def test_heartbeat_requires_matching_active_lease():
    lease = WorkerLease(
        id="11111111-1111-1111-1111-111111111111",
        task_id="22222222-2222-2222-2222-222222222222",
        worker_key="worker-a",
        lease_token="33333333-3333-3333-3333-333333333333",
        expires_at="later",
    )
    db = FakeDb([RowcountResult(1)])

    assert heartbeat_task_lease(db, lease, lease_seconds=60) is True
    sql, params = db.calls[0]
    assert "status='active'" in sql
    assert params["token"] == lease.lease_token
    assert params["seconds"] == 60


def test_release_consumes_only_owned_active_lease():
    lease = WorkerLease(
        id="11111111-1111-1111-1111-111111111111",
        task_id="22222222-2222-2222-2222-222222222222",
        worker_key="worker-a",
        lease_token="33333333-3333-3333-3333-333333333333",
        expires_at="later",
    )
    db = FakeDb([RowcountResult(1)])

    assert release_task_lease(db, lease, recovered=True) is True
    sql, params = db.calls[0]
    assert "lease_token=cast(:token as uuid)" in sql
    assert params["status"] == "recovered"
