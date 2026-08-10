"""Durable Pauli Mission Control worker.

This worker owns deterministic mission state. Agent/model runtimes are bounded
providers beneath it. It never marks work complete merely because a model call
returned; completion requires persisted evidence/verification.
"""
from __future__ import annotations

from typing import Any

from celery import shared_task
from sqlalchemy import text

from models.base import SessionLocal


DEFAULT_WORKFLOW_KEY = "agentforge-production-loop-v1"


@shared_task(name="workers.mission_control.tick", bind=True, max_retries=0)
def mission_control_tick(self) -> dict[str, Any]:
    db = SessionLocal()
    claimed: dict[str, Any] | None = None
    try:
        claimed = db.execute(
            text(
                """
                select m.id, m.organization_id, m.correlation_id, m.status, m.title,
                       m.intent_original, m.requested_outcome, m.workflow_definition_id
                from pauli.missions m
                where m.status in ('INTENT','UNDERSTOOD','PLANNED','STAFFED','PROVISIONED','RECOVERING')
                order by m.priority desc, m.created_at asc
                for update skip locked
                limit 1
                """
            )
        ).mappings().first()
        if not claimed:
            db.commit()
            return {"status": "idle", "claimed": 0}

        mission_id = claimed["id"]
        org_id = claimed["organization_id"]
        correlation_id = claimed["correlation_id"]
        status = claimed["status"]

        if status == "INTENT":
            db.execute(
                text(
                    """
                    update pauli.missions
                    set status='UNDERSTOOD', intent_normalized=intent_original, updated_at=now()
                    where id=:mission_id
                    """
                ),
                {"mission_id": mission_id},
            )
            _event(db, org_id, mission_id, correlation_id, "MISSION_UNDERSTOOD", "Mission intent normalized and accepted for planning.")
            db.commit()
            return {"status": "advanced", "mission_id": str(mission_id), "to": "UNDERSTOOD"}

        if status == "UNDERSTOOD":
            workflow = db.execute(
                text(
                    """
                    select id, definition
                    from pauli.workflow_definitions
                    where (organization_id=:org_id or organization_id is null)
                      and workflow_key=:workflow_key and is_active=true
                    order by organization_id nulls last, version desc
                    limit 1
                    """
                ),
                {"org_id": org_id, "workflow_key": DEFAULT_WORKFLOW_KEY},
            ).mappings().first()
            if not workflow:
                _block(db, claimed, "workflow_missing", f"Required workflow {DEFAULT_WORKFLOW_KEY} is not installed")
                db.commit()
                return {"status": "blocked", "mission_id": str(mission_id), "reason": "workflow_missing"}

            db.execute(
                text(
                    """
                    update pauli.missions
                    set workflow_definition_id=:workflow_id, status='PLANNED', updated_at=now()
                    where id=:mission_id
                    """
                ),
                {"workflow_id": workflow["id"], "mission_id": mission_id},
            )
            _materialize_tasks(db, claimed, workflow["definition"] or {})
            _event(db, org_id, mission_id, correlation_id, "MISSION_PLANNED", "AgentForge workflow selected and durable tasks materialized.")
            db.commit()
            return {"status": "advanced", "mission_id": str(mission_id), "to": "PLANNED"}

        if status == "PLANNED":
            agent = db.execute(
                text(
                    """
                    select id from pauli.agents
                    where organization_id=:org_id and agent_key='pauli'
                    limit 1
                    """
                ),
                {"org_id": org_id},
            ).mappings().first()
            if not agent:
                _block(db, claimed, "pauli_agent_missing", "Canonical Pauli agent is not registered")
                db.commit()
                return {"status": "blocked", "mission_id": str(mission_id), "reason": "pauli_agent_missing"}
            db.execute(text("update pauli.missions set status='STAFFED', started_at=coalesce(started_at,now()), updated_at=now() where id=:id"), {"id": mission_id})
            _event(db, org_id, mission_id, correlation_id, "MISSION_STAFFED", "Pauli accepted executive ownership of the mission.")
            db.commit()
            return {"status": "advanced", "mission_id": str(mission_id), "to": "STAFFED"}

        if status in {"STAFFED", "RECOVERING"}:
            provider = db.execute(
                text(
                    """
                    select id, provider_key, name, kind
                    from pauli.runtime_providers
                    where health_status in ('ready','healthy','online')
                      and kind in ('agent','compute','runtime','desktop','container')
                    order by case when provider_key in ('pauli-compute','hermes','local') then 0 else 1 end,
                             last_healthcheck_at desc nulls last
                    limit 1
                    """
                )
            ).mappings().first()
            if not provider:
                _block(db, claimed, "runtime_unavailable", "No healthy execution runtime is registered. Mission remains durable and resumable.")
                db.commit()
                return {"status": "blocked", "mission_id": str(mission_id), "reason": "runtime_unavailable"}

            db.execute(text("update pauli.missions set status='PROVISIONED', updated_at=now() where id=:id"), {"id": mission_id})
            _event(db, org_id, mission_id, correlation_id, "MISSION_PROVISIONED", f"Execution provider selected: {provider['name']}.")
            db.commit()
            return {"status": "advanced", "mission_id": str(mission_id), "to": "PROVISIONED", "provider": provider["provider_key"]}

        if status == "PROVISIONED":
            # The next step must be claimed by a real execution adapter. We publish
            # READY tasks and move the mission to EXECUTING, but never self-certify.
            db.execute(
                text(
                    """
                    update pauli.mission_tasks
                    set status='ready', updated_at=now()
                    where mission_id=:mission_id and status='pending'
                      and coalesce(array_length(depends_on,1),0)=0
                    """
                ),
                {"mission_id": mission_id},
            )
            db.execute(text("update pauli.missions set status='EXECUTING', updated_at=now() where id=:id"), {"id": mission_id})
            _event(db, org_id, mission_id, correlation_id, "MISSION_EXECUTING", "Mission entered execution; ready tasks require real provider results and evidence.")
            db.commit()
            return {"status": "advanced", "mission_id": str(mission_id), "to": "EXECUTING"}

        db.commit()
        return {"status": "noop", "mission_id": str(mission_id), "state": status}
    except Exception as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


def _materialize_tasks(db, mission: dict[str, Any], definition: dict[str, Any]) -> None:
    states = definition.get("states") or ["PLAN", "EXECUTE", "TEST", "CRITIQUE", "REPAIR", "GUARDIAN", "EVIDENCE", "CHECKPOINT", "COMPLETE"]
    for index, state in enumerate(states):
        task_key = str(state).lower().replace(" ", "-")
        db.execute(
            text(
                """
                insert into pauli.mission_tasks(
                    organization_id, mission_id, task_key, title, description,
                    status, required_capabilities, acceptance_contract
                ) values(
                    :org_id, :mission_id, :task_key, :title, :description,
                    'pending', :capabilities, cast(:acceptance as jsonb)
                )
                on conflict (mission_id, task_key) do nothing
                """
            ),
            {
                "org_id": mission["organization_id"],
                "mission_id": mission["id"],
                "task_key": task_key,
                "title": str(state).title(),
                "description": f"AgentForge production state: {state}",
                "capabilities": [],
                "acceptance": '{"requires_evidence":true,"self_certification":false}',
            },
        )


def _block(db, mission: dict[str, Any], incident_type: str, summary: str) -> None:
    db.execute(text("update pauli.missions set status='BLOCKED', updated_at=now() where id=:id"), {"id": mission["id"]})
    db.execute(
        text(
            """
            insert into pauli.incidents(organization_id,mission_id,severity,incident_type,title,summary,status)
            values(:org_id,:mission_id,'error',:incident_type,'Mission blocked',:summary,'open')
            """
        ),
        {"org_id": mission["organization_id"], "mission_id": mission["id"], "incident_type": incident_type, "summary": summary},
    )
    _event(db, mission["organization_id"], mission["id"], mission["correlation_id"], "MISSION_BLOCKED", summary)


def _event(db, org_id, mission_id, correlation_id, event_type: str, summary: str) -> None:
    db.execute(
        text(
            """
            insert into pauli.mission_events(organization_id,mission_id,correlation_id,event_type,source,public_summary,payload)
            values(:org_id,:mission_id,:correlation_id,:event_type,'mission-control',:summary,'{}'::jsonb)
            """
        ),
        {"org_id": org_id, "mission_id": mission_id, "correlation_id": correlation_id, "event_type": event_type, "summary": summary},
    )
