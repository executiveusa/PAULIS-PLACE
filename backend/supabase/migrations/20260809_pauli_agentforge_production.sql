-- Pauli's Place AgentForge production hardening.
-- This migration is idempotent and assumes the base pauli control-plane schema exists.

create index if not exists pauli_world_presence_agent_idx on pauli.world_presence(agent_id);

create table if not exists pauli.tool_runs (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  mission_id uuid references pauli.missions(id) on delete cascade,
  task_id uuid references pauli.mission_tasks(id) on delete set null,
  agent_id uuid references pauli.agents(id) on delete set null,
  provider text not null,
  toolkit text,
  tool_key text not null,
  action_class text not null check (action_class in ('READ','WRITE','SEND','PUBLISH','DELETE','FINANCIAL','PRODUCTION','IRREVERSIBLE','COMPUTER_CONTROL')),
  approval_id uuid references pauli.approvals(id) on delete set null,
  idempotency_key text not null,
  status text not null default 'queued' check (status in ('queued','running','waiting_approval','blocked','completed','failed','cancelled')),
  request_redacted jsonb not null default '{}'::jsonb,
  response_redacted jsonb not null default '{}'::jsonb,
  cost_cents integer not null default 0 check (cost_cents >= 0),
  latency_ms integer,
  error_class text,
  error_message text,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  unique (organization_id, idempotency_key)
);

create table if not exists pauli.agent_evaluations (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  agent_id uuid references pauli.agents(id) on delete set null,
  mission_id uuid references pauli.missions(id) on delete cascade,
  task_id uuid references pauli.mission_tasks(id) on delete set null,
  evaluation_type text not null default 'gauntlet',
  reference_key text,
  result text not null check (result in ('ours_wins','reference_wins','blocked','vetoed')),
  biggest_gap text,
  critic_model text,
  evidence jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists pauli.incidents (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  mission_id uuid references pauli.missions(id) on delete set null,
  agent_id uuid references pauli.agents(id) on delete set null,
  severity text not null check (severity in ('info','warning','error','critical')),
  incident_type text not null,
  title text not null,
  summary text not null,
  status text not null default 'open' check (status in ('open','acknowledged','recovering','resolved')),
  details_redacted jsonb not null default '{}'::jsonb,
  detected_at timestamptz not null default now(),
  resolved_at timestamptz
);

create table if not exists pauli.model_route_decisions (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  mission_id uuid references pauli.missions(id) on delete cascade,
  task_id uuid references pauli.mission_tasks(id) on delete set null,
  agent_id uuid references pauli.agents(id) on delete set null,
  route_key text not null,
  requirements jsonb not null default '{}'::jsonb,
  candidates jsonb not null default '[]'::jsonb,
  selected_provider text,
  selected_model text,
  estimated_cost_cents integer not null default 0,
  requires_human_approval boolean not null default false,
  rationale text,
  created_at timestamptz not null default now()
);

alter table pauli.tool_runs enable row level security;
alter table pauli.agent_evaluations enable row level security;
alter table pauli.incidents enable row level security;
alter table pauli.model_route_decisions enable row level security;

create index if not exists pauli_tool_runs_org_created_idx on pauli.tool_runs(organization_id, created_at desc);
create index if not exists pauli_tool_runs_mission_idx on pauli.tool_runs(mission_id);
create index if not exists pauli_tool_runs_task_idx on pauli.tool_runs(task_id);
create index if not exists pauli_tool_runs_agent_idx on pauli.tool_runs(agent_id);
create index if not exists pauli_tool_runs_approval_idx on pauli.tool_runs(approval_id);
create index if not exists pauli_evals_org_created_idx on pauli.agent_evaluations(organization_id, created_at desc);
create index if not exists pauli_evals_agent_idx on pauli.agent_evaluations(agent_id);
create index if not exists pauli_evals_mission_idx on pauli.agent_evaluations(mission_id);
create index if not exists pauli_evals_task_idx on pauli.agent_evaluations(task_id);
create index if not exists pauli_incidents_org_status_idx on pauli.incidents(organization_id, status, detected_at desc);
create index if not exists pauli_incidents_mission_idx on pauli.incidents(mission_id);
create index if not exists pauli_incidents_agent_idx on pauli.incidents(agent_id);
create index if not exists pauli_routes_org_created_idx on pauli.model_route_decisions(organization_id, created_at desc);
create index if not exists pauli_routes_mission_idx on pauli.model_route_decisions(mission_id);
create index if not exists pauli_routes_task_idx on pauli.model_route_decisions(task_id);
create index if not exists pauli_routes_agent_idx on pauli.model_route_decisions(agent_id);

do $$ begin
  create policy tool_runs_member_read on pauli.tool_runs for select to authenticated using (pauli_private.is_org_member(organization_id));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy agent_evaluations_member_read on pauli.agent_evaluations for select to authenticated using (pauli_private.is_org_member(organization_id));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy incidents_member_read on pauli.incidents for select to authenticated using (pauli_private.is_org_member(organization_id));
exception when duplicate_object then null; end $$;
do $$ begin
  create policy model_routes_member_read on pauli.model_route_decisions for select to authenticated using (pauli_private.is_org_member(organization_id));
exception when duplicate_object then null; end $$;

grant select on pauli.tool_runs, pauli.agent_evaluations, pauli.incidents, pauli.model_route_decisions to authenticated;
revoke all on pauli.tool_runs, pauli.agent_evaluations, pauli.incidents, pauli.model_route_decisions from anon;

create table if not exists pauli_private.owner_allowlist (
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  email text not null,
  role text not null default 'owner' check (role in ('owner','admin','operator','reviewer','viewer')),
  created_at timestamptz not null default now(),
  primary key (organization_id,email)
);

create or replace function pauli_private.bootstrap_allowlisted_membership()
returns trigger
language plpgsql
security definer
set search_path = pg_catalog
as $$
begin
  insert into pauli.memberships(organization_id,user_id,role,status)
  select a.organization_id,new.id,a.role,'active'
  from pauli_private.owner_allowlist a
  where lower(a.email)=lower(new.email)
  on conflict (organization_id,user_id) do update set role=excluded.role,status='active',updated_at=now();
  return new;
end;
$$;
revoke all on function pauli_private.bootstrap_allowlisted_membership() from public,anon,authenticated;

drop trigger if exists pauli_bootstrap_allowlisted_membership on auth.users;
create trigger pauli_bootstrap_allowlisted_membership
after insert or update of email on auth.users
for each row execute function pauli_private.bootstrap_allowlisted_membership();

insert into pauli.workflow_definitions(organization_id, workflow_key, name, description, version, definition, is_active)
select o.id, 'agentforge-production-loop-v1', 'AgentForge Production Loop',
       'Durable governed execution loop for non-trivial agent work: plan, execute, verify, critique, repair, evidence, checkpoint, resume.',
       1,
       jsonb_build_object(
         'deterministic_owner','mission-control',
         'agent_nodes_bounded',true,
         'states',jsonb_build_array('PLAN','EXECUTE','TEST','CRITIQUE','REPAIR','GUARDIAN','EVIDENCE','CHECKPOINT','COMPLETE'),
         'failure_policy',jsonb_build_object('silent_fallback',false,'resume',true,'strategy_changes',10,'escalate_on',jsonb_build_array('new_authority','new_money','irreversible_action','materially_distinct_strategies_exhausted')),
         'tool_policy',jsonb_build_object('idempotency_required',true,'approval_classes',jsonb_build_array('SEND','PUBLISH','PRODUCTION','IRREVERSIBLE')),
         'memory_policy',jsonb_build_object('namespace_required',true,'prompt_requires_safe_flag',true),
         'evidence_policy',jsonb_build_object('independent_verifier',true,'self_certification',false),
         'gauntlet',jsonb_build_object('fresh_critic',true,'binary_winner',true,'repeat_until_win',true)
       ), true
from pauli.organizations o where o.slug='paulis-place'
on conflict (organization_id, workflow_key, version) do update set definition=excluded.definition, description=excluded.description, is_active=true, updated_at=now();

insert into pauli.workflow_definitions(organization_id, workflow_key, name, description, version, definition, is_active)
select o.id, 'golden-path-nonprofit-v1', 'Golden Path: Nonprofit Vibe Rescue',
       'Voice intent to researched nonprofit prototype, independent verification, preview deployment, evidence, and human callback. No external outreach on first run.',
       1,
       jsonb_build_object(
         'entrypoint','voice_or_text_intent',
         'completion_level','DEPLOYED',
         'budget_cents',1000,
         'steps', jsonb_build_array(
           jsonb_build_object('key','qualify','role','researcher','capabilities',jsonb_build_array('web-research')),
           jsonb_build_object('key','brief','role','strategist','depends_on',jsonb_build_array('qualify')),
           jsonb_build_object('key','build','role','builder','depends_on',jsonb_build_array('brief'),'capabilities',jsonb_build_array('coding','browser')),
           jsonb_build_object('key','gauntlet','role','critic','depends_on',jsonb_build_array('build'),'fresh_context',true),
           jsonb_build_object('key','repair','role','builder','depends_on',jsonb_build_array('gauntlet'),'loop_until','ours_wins_or_guardian_veto'),
           jsonb_build_object('key','deploy_preview','role','publisher','depends_on',jsonb_build_array('repair'),'action_class','WRITE','production',false),
           jsonb_build_object('key','prepare_outreach','role','sales','depends_on',jsonb_build_array('deploy_preview'),'action_class','READ','send',false),
           jsonb_build_object('key','call_owner','role','pauli','depends_on',jsonb_build_array('deploy_preview'),'action_class','SEND','requires_human_scope',true)
         ),
         'guardian', jsonb_build_object('veto_over_gauntlet',true),
         'external_outreach','human_approval_required'
       ), true
from pauli.organizations o where o.slug='paulis-place'
on conflict (organization_id, workflow_key, version) do update set definition=excluded.definition, description=excluded.description, is_active=true, updated_at=now();
