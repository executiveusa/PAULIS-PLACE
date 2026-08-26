"""Bounded execution worker for durable Pauli mission tasks.

Cognitive steps run through the strict AgentForge-inspired model runtime.
Actuator steps require an explicitly healthy provider implementing
`pauli-runtime-v1`; they never degrade into a language-model simulation.
"""
from __future__ import annotations

import asyncio
import json
import threading
from contextlib import contextmanager
from typing import Any

import httpx
from celery import shared_task
from sqlalchemy import text

from models.base import SessionLocal
from services.agent_runtime import (
    AgentPersona,
    ModelRoute,
    NonRetriableRuntimeError,
    RuntimeRequest,
    TransientRuntimeError,
    agent_runtime,
)
from services.capability_guard import authorize_task_capabilities, consume_approval_and_spend, redact_secrets
from services.worker_leases import (
    DEFAULT_LEASE_SECONDS,
    WORKER_KEY,
    WorkerLease,
    acquire_task_lease,
    heartbeat_task_lease,
    reclaim_expired_leases,
    release_task_lease,
)

MODEL_TASKS = {"plan", "critique", "guardian"}
ACTUATOR_TASKS = {"execute", "test", "repair"}
DETERMINISTIC_TASKS = {"checkpoint", "complete"}


@shared_task(name="workers.task_execution.tick", bind=True, max_retries=0)
def task_execution_tick(self) -> dict[str, Any]:
    db = SessionLocal()
    task: dict[str, Any] | None = None
    lease: WorkerLease | None = None
    try:
        reclaimed = reclaim_expired_leases(db)
        if reclaimed:
            db.commit()

        worker_key = getattr(getattr(self, "request", None), "hostname", None) or WORKER_KEY
        task = _claim_ready_task(db, worker_key=worker_key)
        if not task:
            db.commit()
            return {"status": "idle", "claimed": 0, "reclaimed": reclaimed}

        lease = task.pop("_worker_lease")
        db.commit()

        with _lease_heartbeat(lease):
            if task["task_key"] in MODEL_TASKS:
                result = _execute_model_task(db, task)
            elif task["task_key"] in ACTUATOR_TASKS:
                result = _execute_actuator_task(db, task)
            elif task["task_key"] == "evidence":
                result = _verify_evidence(db, task)
            elif task["task_key"] == "checkpoint":
                result = _create_checkpoint(db, task)
            elif task["task_key"] == "complete":
                result = _complete_if_verified(db, task)
            else:
                result = _block_task(db, task, "unsupported_task", f"No governed executor is registered for '{task['task_key']}'.")

        _release_next_task(db, task["mission_id"])
        release_task_lease(db, lease, recovered=result.get("status") == "recovering")
        _mark_agent_after_task(db, task, result)
        db.commit()
        return {**result, "worker_key": lease.worker_key, "lease_id": lease.id, "reclaimed": reclaimed}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def _lease_heartbeat(lease: WorkerLease):
    """Renew a lease from an independent DB session while bounded work runs."""
    stop = threading.Event()
    interval = max(10, DEFAULT_LEASE_SECONDS // 3)

    def beat() -> None:
        while not stop.wait(interval):
            heartbeat_db = SessionLocal()
            try:
                if not heartbeat_task_lease(heartbeat_db, lease):
                    heartbeat_db.rollback()
                    return
                heartbeat_db.commit()
            except Exception:
                heartbeat_db.rollback()
                return
            finally:
                heartbeat_db.close()

    thread = threading.Thread(target=beat, name=f"pauli-lease-{lease.id}", daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=2)


def _claim_ready_task(db, worker_key: str = WORKER_KEY):
    row = db.execute(
        text(
            """
            select t.*, m.title as mission_title, m.intent_original, m.requested_outcome,
                   m.correlation_id, m.status as mission_status
            from pauli.mission_tasks t
            join pauli.missions m on m.id=t.mission_id
            where t.status='ready' and m.status='EXECUTING'
            order by t.created_at asc
            for update of t skip locked
            limit 1
            """
        )
    ).mappings().first()
    if not row:
        return None

    lease = acquire_task_lease(db, row["id"], row["organization_id"], worker_key=worker_key)
    if not lease:
        return None

    db.execute(
        text(
            """
            update pauli.mission_tasks
               set status='running', started_at=coalesce(started_at,now()),
                   attempt_count=attempt_count+1, updated_at=now()
             where id=:id and status='ready'
            """
        ),
        {"id": row["id"]},
    )
    task = dict(row)
    task["_worker_lease"] = lease
    _mark_agent_working(db, task)
    _event(db, task, "TASK_LEASE_ACQUIRED", f"Worker {worker_key} acquired durable task lease.")
    return task


def _mark_agent_working(db, task: dict[str, Any]) -> None:
    db.execute(
        text(
            """
            update pauli.agents
               set status='working', last_heartbeat_at=now(), updated_at=now()
             where id=coalesce(
               :assigned,
               (select id from pauli.agents where organization_id=:org and agent_key='pauli' limit 1)
             )
            """
        ),
        {"assigned": task.get("assigned_agent_id"), "org": task["organization_id"]},
    )


def _mark_agent_after_task(db, task: dict[str, Any], result: dict[str, Any]) -> None:
    next_status = "recovering" if result.get("status") == "recovering" else ("blocked" if result.get("status") == "blocked" else "idle")
    db.execute(
        text(
            """
            update pauli.agents
               set status=:status, last_heartbeat_at=now(), updated_at=now()
             where id=coalesce(
               :assigned,
               (select id from pauli.agents where organization_id=:org and agent_key='pauli' limit 1)
             )
            """
        ),
        {"status": next_status, "assigned": task.get("assigned_agent_id"), "org": task["organization_id"]},
    )


def _execute_model_task(db, task: dict[str, Any]) -> dict[str, Any]:
    agent = _agent_for_task(db, task)
    persona = AgentPersona(
        agent_key=agent["agent_key"], name=agent["name"], role=agent["role"],
        specialty=agent.get("specialty") or "", identity=agent.get("identity") or {},
        heart=agent.get("heart") or {}, soul=agent.get("soul") or {}, skill_manifest=agent.get("skill_manifest") or {},
    )
    prior = _prior_results(db, task["mission_id"])
    routes = agent_runtime.candidate_routes(task["task_key"])

    def make_request(route: ModelRoute) -> RuntimeRequest:
        return RuntimeRequest(
            persona=persona,
            route=route,
            task_key=task["task_key"],
            mission_title=task["mission_title"],
            mission_intent=task["intent_original"],
            requested_outcome=task["requested_outcome"],
            task_description=task.get("description") or task["title"],
            context={"prior_task_results": prior},
        )

    route_id = db.execute(
        text(
            """
            insert into pauli.model_route_decisions(
              organization_id,mission_id,task_id,agent_id,route_key,requirements,candidates,rationale
            ) values(:org,:mission,:task,:agent,:route_key,cast(:requirements as jsonb),cast(:candidates as jsonb),:rationale)
            returning id
            """
        ),
        {
            "org": task["organization_id"], "mission": task["mission_id"], "task": task["id"], "agent": agent["id"],
            "route_key": task["task_key"],
            "requirements": json.dumps({"task_key": task["task_key"], "model_allowed": True}),
            "candidates": json.dumps([{"route_key": r.route_key, "provider": r.provider, "model": r.model} for r in routes]),
            "rationale": "AgentForge-style bounded cognitive route; agent identity remains provider-independent.",
        },
    ).scalar_one()

    run_id = db.execute(
        text(
            """
            insert into pauli.runtime_runs(organization_id,mission_id,task_id,agent_id,status,input_manifest,attempt)
            values(:org,:mission,:task,:agent,'running',cast(:input as jsonb),:attempt) returning id
            """
        ),
        {"org": task["organization_id"], "mission": task["mission_id"], "task": task["id"], "agent": agent["id"], "input": json.dumps({"task_key": task["task_key"]}), "attempt": task["attempt_count"] + 1},
    ).scalar_one()

    try:
        result = asyncio.run(agent_runtime.execute(make_request, task["task_key"]))
    except NonRetriableRuntimeError as exc:
        db.execute(text("update pauli.runtime_runs set status='failed', error_class='non_retriable', error_message=:message, completed_at=now() where id=:id"), {"message": str(exc)[:1000], "id": run_id})
        return _block_task(db, task, "model_runtime_non_retriable", str(exc))
    except TransientRuntimeError as exc:
        db.execute(text("update pauli.runtime_runs set status='failed', error_class='transient_exhausted', error_message=:message, completed_at=now() where id=:id"), {"message": str(exc)[:1000], "id": run_id})
        return _recover_task(db, task, "model_runtime_exhausted", str(exc))

    cost_cents = 0
    db.execute(
        text(
            """
            update pauli.runtime_runs set provider_id=(select id from pauli.runtime_providers where provider_key=:provider limit 1),
              model_key=:model,status='completed',output_manifest=cast(:output as jsonb),
              token_usage=cast(:tokens as jsonb),cost_cents=:cost,latency_ms=:latency,completed_at=now()
            where id=:id
            """
        ),
        {
            "provider": result.provider, "model": result.model, "output": json.dumps({"content": result.content}),
            "tokens": json.dumps({"input": result.input_tokens, "output": result.output_tokens}), "cost": cost_cents,
            "latency": result.latency_ms, "id": run_id,
        },
    )
    db.execute(text("update pauli.model_route_decisions set selected_provider=:provider,selected_model=:model,estimated_cost_cents=:cost where id=:id"), {"provider": result.provider, "model": result.model, "cost": cost_cents, "id": route_id})
    db.execute(text("update pauli.mission_tasks set status='verified', result=cast(:result as jsonb), completed_at=now(), updated_at=now() where id=:id"), {"result": json.dumps({"content": result.content, "provider": result.provider, "model": result.model, "runtime_run_id": str(run_id)}), "id": task["id"]})
    _event(db, task, "TASK_VERIFIED", f"Cognitive task '{task['task_key']}' completed by {result.provider}/{result.model}.")
    return {"status": "verified", "task_id": str(task["id"]), "task_key": task["task_key"], "provider": result.provider, "model": result.model}


def _execute_actuator_task(db, task: dict[str, Any]) -> dict[str, Any]:
    estimated_spend_cents = int((task.get("acceptance_contract") or {}).get("estimated_spend_cents", 0) or 0)
    decisions = authorize_task_capabilities(db, task, estimated_spend_cents=estimated_spend_cents)
    denied = next((decision for decision in decisions if not decision.allowed), None)
    if denied:
        event_type = "TASK_APPROVAL_REQUIRED" if denied.decision == "approval_required" else "TASK_CAPABILITY_DENIED"
        _event(db, task, event_type, f"Capability '{denied.capability_key}' denied: {denied.reason}")
        return _block_task(db, task, denied.decision, denied.reason)

    provider = db.execute(
        text(
            """
            select id,provider_key,name,endpoint_ref,capabilities,metadata
            from pauli.runtime_providers
            where health_status in ('ready','healthy','online') and endpoint_ref is not null
              and coalesce(metadata->>'protocol','')='pauli-runtime-v1'
            order by last_healthcheck_at desc nulls last
            limit 1
            """
        )
    ).mappings().first()
    if not provider:
        return _block_task(db, task, "actuator_unavailable", f"Task '{task['task_key']}' requires a healthy pauli-runtime-v1 actuator provider.")

    payload = redact_secrets({
        "mission": {"id": str(task["mission_id"]), "title": task["mission_title"], "intent": task["intent_original"], "requested_outcome": task["requested_outcome"]},
        "task": {"id": str(task["id"]), "key": task["task_key"], "title": task["title"], "description": task.get("description")},
        "prior_results": _prior_results(db, task["mission_id"]),
        "contract": {
            "protocol": "pauli-runtime-v1",
            "requires_evidence": True,
            "self_certification": False,
            "capabilities": [decision.capability_key for decision in decisions],
        },
    })
    run_id = db.execute(
        text("insert into pauli.runtime_runs(organization_id,mission_id,task_id,provider_id,status,input_manifest,attempt) values(:org,:mission,:task,:provider,'running',cast(:input as jsonb),:attempt) returning id"),
        {"org": task["organization_id"], "mission": task["mission_id"], "task": task["id"], "provider": provider["id"], "input": json.dumps(payload), "attempt": task["attempt_count"] + 1},
    ).scalar_one()

    try:
        response = httpx.post(provider["endpoint_ref"], json=payload, timeout=300.0)
        if response.status_code in {400, 401, 403, 404, 405, 422}:
            raise NonRetriableRuntimeError(f"actuator rejected request ({response.status_code}): {response.text[:240]}")
        response.raise_for_status()
        body = redact_secrets(response.json())
    except NonRetriableRuntimeError as exc:
        db.execute(text("update pauli.runtime_runs set status='failed',error_class='non_retriable',error_message=:error,completed_at=now() where id=:id"), {"error": str(exc)[:1000], "id": run_id})
        return _block_task(db, task, "actuator_rejected", str(exc))
    except (httpx.HTTPError, ValueError) as exc:
        db.execute(text("update pauli.runtime_runs set status='failed',error_class='provider_error',error_message=:error,completed_at=now() where id=:id"), {"error": str(exc)[:1000], "id": run_id})
        return _recover_task(db, task, "actuator_error", str(exc))

    status = str(body.get("status", "")).lower()
    evidence = body.get("evidence") or []
    if status not in {"completed", "verified"} or not evidence:
        db.execute(text("update pauli.runtime_runs set status='failed',error_class='evidence_missing',error_message='provider returned no verifiable evidence',output_manifest=cast(:output as jsonb),completed_at=now() where id=:id"), {"output": json.dumps(body), "id": run_id})
        return _block_task(db, task, "evidence_missing", f"Provider {provider['provider_key']} returned no verifiable evidence.")

    consume_approval_and_spend(db, task, decisions)
    db.execute(text("update pauli.runtime_runs set status='completed',output_manifest=cast(:output as jsonb),completed_at=now() where id=:id"), {"output": json.dumps(body), "id": run_id})
    db.execute(text("update pauli.mission_tasks set status='verified',result=cast(:result as jsonb),completed_at=now(),updated_at=now() where id=:id"), {"result": json.dumps(body), "id": task["id"]})
    db.execute(
        text("insert into pauli.evidence_receipts(organization_id,mission_id,task_id,runtime_run_id,status,summary,tests,artifacts,verification) values(:org,:mission,:task,:run,'verified',:summary,cast(:tests as jsonb),cast(:artifacts as jsonb),cast(:verification as jsonb))"),
        {"org": task["organization_id"], "mission": task["mission_id"], "task": task["id"], "run": run_id, "summary": f"Verified actuator output from {provider['name']}", "tests": json.dumps(body.get("tests") or []), "artifacts": json.dumps(evidence), "verification": json.dumps({"provider": provider["provider_key"], "protocol": "pauli-runtime-v1", "capabilities": [decision.capability_key for decision in decisions]})},
    )
    _event(db, task, "TASK_VERIFIED", f"Actuator task '{task['task_key']}' verified with provider evidence.")
    return {"status": "verified", "task_id": str(task["id"]), "provider": provider["provider_key"]}


def _verify_evidence(db, task: dict[str, Any]) -> dict[str, Any]:
    count = db.execute(text("select count(*) from pauli.evidence_receipts where mission_id=:mission and status='verified'"), {"mission": task["mission_id"]}).scalar_one()
    if count < 1:
        return _block_task(db, task, "evidence_gate_failed", "No independently persisted verified evidence exists for this mission.")
    db.execute(text("update pauli.mission_tasks set status='verified',result=cast(:result as jsonb),completed_at=now(),updated_at=now() where id=:id"), {"result": json.dumps({"verified_receipts": count}), "id": task["id"]})
    _event(db, task, "EVIDENCE_GATE_PASSED", f"Evidence gate passed with {count} verified receipt(s).")
    return {"status": "verified", "task_id": str(task["id"]), "verified_receipts": count}


def _create_checkpoint(db, task: dict[str, Any]) -> dict[str, Any]:
    state = _prior_results(db, task["mission_id"])
    checkpoint_id = db.execute(
        text("insert into pauli.checkpoints(organization_id,mission_id,task_id,stage_key,reason,state_manifest,verified) values(:org,:mission,:task,'pre-complete','AgentForge durable checkpoint',cast(:state as jsonb),true) returning id"),
        {"org": task["organization_id"], "mission": task["mission_id"], "task": task["id"], "state": json.dumps(state)},
    ).scalar_one()
    db.execute(text("update pauli.mission_tasks set status='verified',result=cast(:result as jsonb),completed_at=now(),updated_at=now() where id=:id"), {"result": json.dumps({"checkpoint_id": str(checkpoint_id)}), "id": task["id"]})
    return {"status": "verified", "task_id": str(task["id"]), "checkpoint_id": str(checkpoint_id)}


def _complete_if_verified(db, task: dict[str, Any]) -> dict[str, Any]:
    incomplete = db.execute(text("select count(*) from pauli.mission_tasks where mission_id=:mission and id<>:task and status<>'verified'"), {"mission": task["mission_id"], "task": task["id"]}).scalar_one()
    evidence = db.execute(text("select count(*) from pauli.evidence_receipts where mission_id=:mission and status='verified'"), {"mission": task["mission_id"]}).scalar_one()
    if incomplete or evidence < 1:
        return _block_task(db, task, "completion_gate_failed", f"Completion gate failed: incomplete_tasks={incomplete}, verified_evidence={evidence}.")
    db.execute(text("update pauli.mission_tasks set status='verified',result='{" + '"completion_gate":true' + "}'::jsonb,completed_at=now(),updated_at=now() where id=:id"), {"id": task["id"]})
    db.execute(text("update pauli.missions set status='OUTCOME_ACHIEVED',completed_at=now(),updated_at=now() where id=:mission"), {"mission": task["mission_id"]})
    _event(db, task, "MISSION_OUTCOME_ACHIEVED", "All durable task and evidence gates passed.")
    return {"status": "outcome_achieved", "mission_id": str(task["mission_id"])}


def _release_next_task(db, mission_id) -> None:
    db.execute(
        text(
            """
            update pauli.mission_tasks candidate
               set status='ready',updated_at=now()
             where candidate.id = (
               select t.id
                 from pauli.mission_tasks t
                where t.mission_id=:mission
                  and t.status='pending'
                  and not exists (
                    select 1 from unnest(t.depends_on) dep
                    join pauli.mission_tasks d on d.id=dep
                    where d.status<>'verified'
                  )
                order by t.created_at asc
                limit 1
             )
            """
        ),
        {"mission": mission_id},
    )


def _agent_for_task(db, task: dict[str, Any]):
    row = db.execute(
        text(
            """
            select * from pauli.agents
             where id=coalesce(:assigned,(select id from pauli.agents where organization_id=:org and agent_key='pauli' limit 1))
             limit 1
            """
        ),
        {"assigned": task.get("assigned_agent_id"), "org": task["organization_id"]},
    ).mappings().first()
    if not row:
        raise NonRetriableRuntimeError("No persistent Pauli agent identity is available for task execution.")
    return dict(row)


def _prior_results(db, mission_id) -> list[dict[str, Any]]:
    rows = db.execute(
        text("select task_key,status,result from pauli.mission_tasks where mission_id=:mission and status='verified' order by created_at asc"),
        {"mission": mission_id},
    ).mappings().all()
    return [dict(row) for row in rows]


def _block_task(db, task: dict[str, Any], reason: str, detail: str) -> dict[str, Any]:
    db.execute(text("update pauli.mission_tasks set status='blocked',result=cast(:result as jsonb),updated_at=now() where id=:id"), {"result": json.dumps({"reason": reason, "detail": detail}), "id": task["id"]})
    db.execute(text("update pauli.missions set status='BLOCKED',updated_at=now() where id=:mission and status in ('EXECUTING','RECOVERING')"), {"mission": task["mission_id"]})
    _event(db, task, "TASK_BLOCKED", detail)
    return {"status": "blocked", "task_id": str(task["id"]), "reason": reason}


def _recover_task(db, task: dict[str, Any], reason: str, detail: str) -> dict[str, Any]:
    db.execute(text("update pauli.mission_tasks set status='recovering',result=cast(:result as jsonb),updated_at=now() where id=:id"), {"result": json.dumps({"reason": reason, "detail": detail}), "id": task["id"]})
    db.execute(text("update pauli.missions set status='RECOVERING',updated_at=now() where id=:mission"), {"mission": task["mission_id"]})
    _event(db, task, "TASK_RECOVERING", detail)
    return {"status": "recovering", "task_id": str(task["id"]), "reason": reason}


def _event(db, task: dict[str, Any], event_type: str, summary: str) -> None:
    db.execute(
        text(
            """
            insert into pauli.mission_events(
              organization_id,mission_id,task_id,agent_id,correlation_id,event_type,source,public_summary,payload
            ) values(:org,:mission,:task,:agent,:correlation,:event_type,'task-execution',:summary,'{}'::jsonb)
            """
        ),
        {
            "org": task["organization_id"],
            "mission": task["mission_id"],
            "task": task["id"],
            "agent": task.get("assigned_agent_id"),
            "correlation": task["correlation_id"],
            "event_type": event_type,
            "summary": summary,
        },
    )
