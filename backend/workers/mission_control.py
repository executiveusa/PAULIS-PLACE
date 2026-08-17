"""Durable Pauli Mission Control worker.

Mission Control, not an LLM, owns state transitions. Agent/model runtimes are
bounded providers underneath this state machine. No task is considered complete
without its acceptance/evidence gates.
"""
from __future__ import annotations

from typing import Any

from celery import shared_task
from sqlalchemy import text

from models.base import SessionLocal

DEFAULT_WORKFLOW_KEY = "agentforge-production-loop-v1"
RECOVERABLE_INCIDENTS = {
    "runtime_unavailable",
    "actuator_unavailable",
    "model_runtime_exhausted",
    "actuator_error",
}


@shared_task(name="workers.mission_control.tick", bind=True, max_retries=0)
def mission_control_tick(self) -> dict[str, Any]:
    db = SessionLocal()
    try:
        mission = db.execute(
            text(
                """
                select m.id, m.organization_id, m.correlation_id, m.status, m.title,
                       m.intent_original, m.requested_outcome, m.workflow_definition_id
                from pauli.missions m
                where m.status in ('INTENT','UNDERSTOOD','PLANNED','STAFFED','PROVISIONED','RECOVERING','BLOCKED')
                order by m.priority desc, m.created_at asc
                for update skip locked
                limit 1
                """
            )
        ).mappings().first()
        if not mission:
            db.commit()
            return {"status": "idle", "claimed": 0}

        mission = dict(mission)
        mission_id = mission["id"]
        org_id = mission["organization_id"]
        correlation_id = mission["correlation_id"]
        status = mission["status"]

        if status == "INTENT":
            db.execute(text("update pauli.missions set status='UNDERSTOOD',intent_normalized=intent_original,updated_at=now() where id=:id"), {"id": mission_id})
            _event(db, mission, "MISSION_UNDERSTOOD", "Mission intent normalized and accepted for deterministic planning.")
            db.commit()
            return _advanced(mission_id, "UNDERSTOOD")

        if status == "UNDERSTOOD":
            workflow = db.execute(
                text(
                    """
                    select id,definition from pauli.workflow_definitions
                    where (organization_id=:org or organization_id is null)
                      and workflow_key=:key and is_active=true
                    order by organization_id nulls last,version desc limit 1
                    """
                ),
                {"org": org_id, "key": DEFAULT_WORKFLOW_KEY},
            ).mappings().first()
            if not workflow:
                _block(db, mission, "workflow_missing", f"Required workflow {DEFAULT_WORKFLOW_KEY} is not installed.")
                db.commit()
                return {"status": "blocked", "mission_id": str(mission_id), "reason": "workflow_missing"}
            db.execute(text("update pauli.missions set workflow_definition_id=:workflow,status='PLANNED',updated_at=now() where id=:id"), {"workflow": workflow["id"], "id": mission_id})
            _materialize_tasks(db, mission, workflow["definition"] or {})
            _event(db, mission, "MISSION_PLANNED", "AgentForge workflow selected and sequential durable tasks materialized.")
            db.commit()
            return _advanced(mission_id, "PLANNED")

        if status == "PLANNED":
            agent = db.execute(text("select id from pauli.agents where organization_id=:org and agent_key='pauli' limit 1"), {"org": org_id}).mappings().first()
            if not agent:
                _block(db, mission, "pauli_agent_missing", "Canonical Pauli agent identity is not registered.")
                db.commit()
                return {"status": "blocked", "mission_id": str(mission_id), "reason": "pauli_agent_missing"}
            db.execute(text("update pauli.missions set status='STAFFED',started_at=coalesce(started_at,now()),updated_at=now() where id=:id"), {"id": mission_id})
            _event(db, mission, "MISSION_STAFFED", "Pauli accepted executive ownership of the mission.")
            db.commit()
            return _advanced(mission_id, "STAFFED")

        if status == "STAFFED":
            provider = _healthy_provider(db)
            if not provider:
                _block(db, mission, "runtime_unavailable", "No healthy governed execution runtime is registered. Mission remains durable and resumable.")
                db.commit()
                return {"status": "blocked", "mission_id": str(mission_id), "reason": "runtime_unavailable"}
            db.execute(text("update pauli.missions set status='PROVISIONED',execution_context=execution_context || cast(:context as jsonb),updated_at=now() where id=:id"), {"context": '{"provider_selected":true}', "id": mission_id})
            _event(db, mission, "MISSION_PROVISIONED", f"Execution provider available: {provider['name']}.")
            db.commit()
            return {**_advanced(mission_id, "PROVISIONED"), "provider": provider["provider_key"]}

        if status == "PROVISIONED":
            _release_ready_tasks(db, mission_id)
            db.execute(text("update pauli.missions set status='EXECUTING',updated_at=now() where id=:id"), {"id": mission_id})
            _event(db, mission, "MISSION_EXECUTING", "Mission entered bounded execution. Only dependency-satisfied tasks are ready.")
            db.commit()
            return _advanced(mission_id, "EXECUTING")

        if status == "BLOCKED":
            incident = db.execute(
                text("select incident_type from pauli.incidents where mission_id=:mission and status<>'resolved' order by detected_at desc limit 1"),
                {"mission": mission_id},
            ).mappings().first()
            if not incident or incident["incident_type"] not in RECOVERABLE_INCIDENTS or not _healthy_provider(db):
                db.commit()
                return {"status": "blocked", "mission_id": str(mission_id), "reason": incident["incident_type"] if incident else "unknown"}
            db.execute(text("update pauli.missions set status='RECOVERING',updated_at=now() where id=:id"), {"id": mission_id})
            db.execute(text("update pauli.incidents set status='recovering' where mission_id=:mission and status in ('open','acknowledged') and incident_type=:type"), {"mission": mission_id, "type": incident["incident_type"]})
            _event(db, mission, "MISSION_RECOVERING", f"Recoverable blocker changed: {incident['incident_type']}.")
            db.commit()
            return _advanced(mission_id, "RECOVERING")

        if status == "RECOVERING":
            db.execute(text("update pauli.mission_tasks set status='pending',updated_at=now() where mission_id=:mission and status in ('blocked','recovering')"), {"mission": mission_id})
            _release_ready_tasks(db, mission_id)
            db.execute(text("update pauli.missions set status='EXECUTING',updated_at=now() where id=:id"), {"id": mission_id})
            _event(db, mission, "MISSION_RESUMED", "Mission resumed from the last durable task boundary.")
            db.commit()
            return _advanced(mission_id, "EXECUTING")

        db.commit()
        return {"status": "noop", "mission_id": str(mission_id), "state": status}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _materialize_tasks(db, mission: dict[str, Any], definition: dict[str, Any]) -> None:
    states = definition.get("states") or ["PLAN", "EXECUTE", "TEST", "CRITIQUE", "REPAIR", "GUARDIAN", "EVIDENCE", "CHECKPOINT", "COMPLETE"]
    previous_id = None
    for state in states:
        task_key = str(state).lower().replace(" ", "-")
        dependencies = [] if previous_id is None else [previous_id]
        row = db.execute(
            text(
                """
                insert into pauli.mission_tasks(
                  organization_id,mission_id,task_key,title,description,status,
                  depends_on,required_capabilities,acceptance_contract
                ) values(
                  :org,:mission,:key,:title,:description,'pending',:depends_on,:capabilities,cast(:acceptance as jsonb)
                )
                on conflict (mission_id,task_key) do update
                  set depends_on=excluded.depends_on,
                      acceptance_contract=excluded.acceptance_contract,
                      updated_at=now()
                returning id
                """
            ),
            {
                "org": mission["organization_id"],
                "mission": mission["id"],
                "key": task_key,
                "title": str(state).title(),
                "description": f"AgentForge production state: {state}",
                "depends_on": dependencies,
                "capabilities": _capabilities_for(task_key),
                "acceptance": _acceptance_for(task_key),
            },
        ).mappings().one()
        previous_id = row["id"]


def _capabilities_for(task_key: str) -> list[str]:
    if task_key in {"plan", "critique", "guardian"}:
        return ["model"]
    if task_key in {"execute", "repair"}:
        return ["computer-control", "tool-execution"]
    if task_key == "test":
        return ["test-execution", "evidence"]
    if task_key == "evidence":
        return ["independent-verification"]
    return ["deterministic-control"]


def _acceptance_for(task_key: str) -> str:
    if task_key in {"execute", "test", "repair"}:
        return '{"requires_evidence":true,"self_certification":false,"provider_protocol":"pauli-runtime-v1"}'
    if task_key == "evidence":
        return '{"requires_evidence":true,"minimum_verified_receipts":1,"self_certification":false}'
    return '{"requires_evidence":false,"self_certification":false}'


def _release_ready_tasks(db, mission_id) -> None:
    db.execute(
        text(
            """
            update pauli.mission_tasks t set status='ready',updated_at=now()
            where t.mission_id=:mission and t.status='pending'
              and not exists (
                select 1 from unnest(t.depends_on) dep
                join pauli.mission_tasks prerequisite on prerequisite.id=dep
                where prerequisite.status<>'verified'
              )
            """
        ),
        {"mission": mission_id},
    )


def _healthy_provider(db):
    return db.execute(
        text(
            """
            select id,provider_key,name,kind from pauli.runtime_providers
            where health_status in ('ready','healthy','online')
              and kind in ('agent','agent_runtime','compute','runtime','desktop','container','model')
            order by last_healthcheck_at desc nulls last limit 1
            """
        )
    ).mappings().first()


def _block(db, mission: dict[str, Any], incident_type: str, summary: str) -> None:
    db.execute(text("update pauli.missions set status='BLOCKED',updated_at=now() where id=:id"), {"id": mission["id"]})
    db.execute(
        text("insert into pauli.incidents(organization_id,mission_id,severity,incident_type,title,summary,status) values(:org,:mission,'error',:type,'Mission blocked',:summary,'open')"),
        {"org": mission["organization_id"], "mission": mission["id"], "type": incident_type, "summary": summary},
    )
    _event(db, mission, "MISSION_BLOCKED", summary)


def _event(db, mission: dict[str, Any], event_type: str, summary: str) -> None:
    db.execute(
        text("insert into pauli.mission_events(organization_id,mission_id,correlation_id,event_type,source,public_summary,payload) values(:org,:mission,:correlation,:type,'mission-control',:summary,'{}'::jsonb)"),
        {"org": mission["organization_id"], "mission": mission["id"], "correlation": mission["correlation_id"], "type": event_type, "summary": summary},
    )


def _advanced(mission_id, state: str) -> dict[str, Any]:
    return {"status": "advanced", "mission_id": str(mission_id), "to": state}
