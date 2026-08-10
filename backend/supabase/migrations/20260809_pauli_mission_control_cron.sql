-- Durable server-side Mission Control heartbeat for Pauli's Place.
-- Mirrors the deterministic pre-execution state machine in workers/mission_control.py
-- so voice-created missions progress even when the legacy VPS worker is unavailable.

create extension if not exists pg_cron;

create or replace function pauli_private.mission_control_tick()
returns jsonb
language plpgsql
security definer
set search_path = pg_catalog
as $$
declare
  m record;
  w record;
  a record;
  p record;
  prev_task uuid;
  current_task uuid;
  state_name text;
  states text[];
begin
  select id,organization_id,correlation_id,status,title,intent_original,requested_outcome,workflow_definition_id
  into m
  from pauli.missions
  where status in ('INTENT','UNDERSTOOD','PLANNED','STAFFED','PROVISIONED')
  order by priority desc,created_at asc
  for update skip locked
  limit 1;

  if m.id is null then return jsonb_build_object('status','idle'); end if;

  if m.status='INTENT' then
    update pauli.missions set status='UNDERSTOOD',intent_normalized=intent_original,updated_at=now() where id=m.id;
    insert into pauli.mission_events(organization_id,mission_id,correlation_id,event_type,source,public_summary,payload)
    values(m.organization_id,m.id,m.correlation_id,'MISSION_UNDERSTOOD','supabase-cron','Mission intent normalized and accepted for deterministic planning.','{}'::jsonb);
    return jsonb_build_object('status','advanced','mission_id',m.id,'to','UNDERSTOOD');
  end if;

  if m.status='UNDERSTOOD' then
    select id,definition into w from pauli.workflow_definitions
    where (organization_id=m.organization_id or organization_id is null)
      and workflow_key='agentforge-production-loop-v1' and is_active=true
    order by organization_id nulls last,version desc limit 1;
    if w.id is null then
      update pauli.missions set status='BLOCKED',updated_at=now() where id=m.id;
      insert into pauli.incidents(organization_id,mission_id,severity,incident_type,title,summary,status)
      values(m.organization_id,m.id,'error','workflow_missing','Mission blocked','AgentForge production workflow is not installed.','open');
      return jsonb_build_object('status','blocked','mission_id',m.id,'reason','workflow_missing');
    end if;

    update pauli.missions set workflow_definition_id=w.id,status='PLANNED',updated_at=now() where id=m.id;
    states := array['PLAN','EXECUTE','TEST','CRITIQUE','REPAIR','GUARDIAN','EVIDENCE','CHECKPOINT','COMPLETE'];
    prev_task := null;
    foreach state_name in array states loop
      insert into pauli.mission_tasks(organization_id,mission_id,task_key,title,description,status,depends_on,required_capabilities,acceptance_contract)
      values(
        m.organization_id,m.id,lower(state_name),initcap(lower(state_name)),'AgentForge production state: '||state_name,'pending',
        case when prev_task is null then '{}'::uuid[] else array[prev_task] end,
        case
          when state_name in ('PLAN','CRITIQUE','GUARDIAN') then array['model']::text[]
          when state_name in ('EXECUTE','REPAIR') then array['computer-control','tool-execution']::text[]
          when state_name='TEST' then array['test-execution','evidence']::text[]
          when state_name='EVIDENCE' then array['independent-verification']::text[]
          else array['deterministic-control']::text[]
        end,
        case
          when state_name in ('EXECUTE','TEST','REPAIR') then '{"requires_evidence":true,"self_certification":false,"provider_protocol":"pauli-runtime-v1"}'::jsonb
          when state_name='EVIDENCE' then '{"requires_evidence":true,"minimum_verified_receipts":1,"self_certification":false}'::jsonb
          else '{"requires_evidence":false,"self_certification":false}'::jsonb
        end
      )
      on conflict (mission_id,task_key) do update set depends_on=excluded.depends_on,required_capabilities=excluded.required_capabilities,acceptance_contract=excluded.acceptance_contract,updated_at=now()
      returning id into current_task;
      prev_task := current_task;
    end loop;
    insert into pauli.mission_events(organization_id,mission_id,correlation_id,event_type,source,public_summary,payload)
    values(m.organization_id,m.id,m.correlation_id,'MISSION_PLANNED','supabase-cron','AgentForge workflow selected and sequential durable tasks materialized.','{}'::jsonb);
    return jsonb_build_object('status','advanced','mission_id',m.id,'to','PLANNED');
  end if;

  if m.status='PLANNED' then
    select id into a from pauli.agents where organization_id=m.organization_id and agent_key='pauli' limit 1;
    if a.id is null then
      update pauli.missions set status='BLOCKED',updated_at=now() where id=m.id;
      insert into pauli.incidents(organization_id,mission_id,severity,incident_type,title,summary,status)
      values(m.organization_id,m.id,'error','pauli_agent_missing','Mission blocked','Canonical Pauli agent identity is not registered.','open');
      return jsonb_build_object('status','blocked','mission_id',m.id,'reason','pauli_agent_missing');
    end if;
    update pauli.missions set status='STAFFED',started_at=coalesce(started_at,now()),updated_at=now() where id=m.id;
    return jsonb_build_object('status','advanced','mission_id',m.id,'to','STAFFED');
  end if;

  if m.status='STAFFED' then
    select id,provider_key,name into p from pauli.runtime_providers
    where health_status in ('ready','healthy','online')
      and kind in ('agent','agent_runtime','compute','runtime','desktop','container','model')
    order by last_healthcheck_at desc nulls last limit 1;
    if p.id is null then
      update pauli.missions set status='BLOCKED',updated_at=now() where id=m.id;
      insert into pauli.incidents(organization_id,mission_id,severity,incident_type,title,summary,status)
      values(m.organization_id,m.id,'error','runtime_unavailable','Mission blocked','No healthy governed execution runtime is registered. Mission remains durable and resumable.','open');
      return jsonb_build_object('status','blocked','mission_id',m.id,'reason','runtime_unavailable');
    end if;
    update pauli.missions set status='PROVISIONED',execution_context=execution_context||jsonb_build_object('provider_key',p.provider_key),updated_at=now() where id=m.id;
    return jsonb_build_object('status','advanced','mission_id',m.id,'to','PROVISIONED','provider',p.provider_key);
  end if;

  if m.status='PROVISIONED' then
    update pauli.mission_tasks t set status='ready',updated_at=now()
    where t.mission_id=m.id and t.status='pending'
      and not exists (
        select 1 from unnest(t.depends_on) dep
        join pauli.mission_tasks prerequisite on prerequisite.id=dep
        where prerequisite.status<>'verified'
      );
    update pauli.missions set status='EXECUTING',updated_at=now() where id=m.id;
    return jsonb_build_object('status','advanced','mission_id',m.id,'to','EXECUTING');
  end if;

  return jsonb_build_object('status','noop','mission_id',m.id,'state',m.status);
end;
$$;

revoke all on function pauli_private.mission_control_tick() from public,anon,authenticated;

select cron.unschedule(jobid) from cron.job where jobname='pauli-mission-control';
select cron.schedule('pauli-mission-control','10 seconds',$$select pauli_private.mission_control_tick();$$);
