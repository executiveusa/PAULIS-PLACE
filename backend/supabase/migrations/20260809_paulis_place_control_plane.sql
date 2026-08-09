-- Pauli's Place production control plane for Supabase/Postgres
-- 2026-08-09
-- Additive-only migration. Pauli lives in dedicated schemas inside the shared
-- botanic-creations project. Client/company isolation is by organization_id + RLS.
-- AgentForge concepts absorbed here: persistent personas, declarative workflow
-- definitions, namespaced memory, model/runtime profiles, bounded retries,
-- checkpoints/evidence, and observable execution state.

create extension if not exists pgcrypto;

create schema if not exists pauli;
create schema if not exists pauli_private;

revoke all on schema pauli_private from public, anon, authenticated;
grant usage on schema pauli to authenticated;

create table if not exists pauli.organizations (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  name text not null,
  preferred_language text not null default 'en' check (preferred_language in ('en','es-MX','mixed')),
  status text not null default 'active' check (status in ('active','paused','archived')),
  reserve_rate numeric(5,4) not null default 0.40 check (reserve_rate between 0 and 1),
  reinvestment_ceiling numeric(5,4) not null default 0.60 check (reinvestment_ceiling between 0 and 1),
  default_experiment_budget_cents integer not null default 1000 check (default_experiment_budget_cents >= 0),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists pauli.memberships (
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null default 'viewer' check (role in ('owner','admin','operator','reviewer','viewer')),
  status text not null default 'active' check (status in ('active','invited','suspended','revoked')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (organization_id, user_id)
);

create table if not exists pauli.agents (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  agent_key text not null,
  name text not null,
  role text not null,
  specialty text,
  identity jsonb not null default '{}'::jsonb,
  heart jsonb not null default '{}'::jsonb,
  soul jsonb not null default '{}'::jsonb,
  persona_static jsonb not null default '{}'::jsonb,
  persona_retrieval jsonb not null default '{}'::jsonb,
  skill_manifest jsonb not null default '[]'::jsonb,
  runtime_policy jsonb not null default '{}'::jsonb,
  model_policy jsonb not null default '{}'::jsonb,
  compute_policy jsonb not null default '{}'::jsonb,
  status text not null default 'offline' check (status in ('offline','idle','working','meeting','blocked','waiting_approval','recovering','error')),
  world_location_key text,
  last_heartbeat_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, agent_key)
);

create table if not exists pauli.workflow_definitions (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid references pauli.organizations(id) on delete cascade,
  workflow_key text not null,
  name text not null,
  description text,
  version integer not null default 1 check (version > 0),
  definition jsonb not null,
  -- AgentForge-style declarative flow: nodes, transitions, memory hooks,
  -- fallbacks, max_visits, acceptance and completion contracts.
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, workflow_key, version)
);

create table if not exists pauli.missions (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  created_by uuid references auth.users(id) on delete set null,
  parent_mission_id uuid references pauli.missions(id) on delete set null,
  workflow_definition_id uuid references pauli.workflow_definitions(id) on delete set null,
  correlation_id uuid not null default gen_random_uuid(),
  title text not null,
  intent_original text not null,
  intent_normalized text,
  language text not null default 'en' check (language in ('en','es-MX','mixed')),
  mission_type text,
  requested_outcome text not null,
  required_completion_level text not null default 'OUTCOME_ACHIEVED' check (required_completion_level in ('IMPLEMENTED','VERIFIED','DEPLOYED','HEALTHY','OUTCOME_ACHIEVED','BUSINESS_OUTCOME_MEASURED')),
  status text not null default 'INTENT' check (status in ('INTENT','UNDERSTOOD','PLANNED','STAFFED','PROVISIONED','EXECUTING','WAITING_APPROVAL','BLOCKED','RECOVERING','VERIFYING','DEPLOYED','OUTCOME_PENDING','OUTCOME_ACHIEVED','LEARNED','CLOSED','FAILED','CANCELLED')),
  priority integer not null default 50 check (priority between 0 and 100),
  autonomous_budget_cents integer not null default 0 check (autonomous_budget_cents >= 0),
  spent_cents integer not null default 0 check (spent_cents >= 0),
  attempt_count integer not null default 0 check (attempt_count >= 0),
  policy_snapshot jsonb not null default '{}'::jsonb,
  execution_context jsonb not null default '{}'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists pauli.mission_tasks (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  mission_id uuid not null references pauli.missions(id) on delete cascade,
  assigned_agent_id uuid references pauli.agents(id) on delete set null,
  task_key text not null,
  title text not null,
  description text,
  status text not null default 'pending' check (status in ('pending','ready','running','blocked','waiting_approval','recovering','verifying','verified','failed','cancelled')),
  depends_on uuid[] not null default '{}'::uuid[],
  required_capabilities text[] not null default '{}'::text[],
  acceptance_contract jsonb not null default '{}'::jsonb,
  retry_policy jsonb not null default '{"max_strategy_changes":10,"backoff":"exponential","fail_fast_non_retriable":true}'::jsonb,
  result jsonb not null default '{}'::jsonb,
  attempt_count integer not null default 0,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (mission_id, task_key)
);

create table if not exists pauli.mission_events (
  id bigint generated by default as identity primary key,
  event_uuid uuid not null default gen_random_uuid() unique,
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  mission_id uuid not null references pauli.missions(id) on delete cascade,
  task_id uuid references pauli.mission_tasks(id) on delete set null,
  agent_id uuid references pauli.agents(id) on delete set null,
  correlation_id uuid not null,
  causation_id uuid,
  event_type text not null,
  source text not null default 'pauli',
  idempotency_key text,
  public_summary text,
  payload jsonb not null default '{}'::jsonb,
  visibility text not null default 'tenant' check (visibility in ('public','member','tenant','team','private','system')),
  occurred_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  unique (organization_id, idempotency_key)
);

create table if not exists pauli.approvals (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  mission_id uuid references pauli.missions(id) on delete cascade,
  task_id uuid references pauli.mission_tasks(id) on delete set null,
  requested_by_agent_id uuid references pauli.agents(id) on delete set null,
  decided_by uuid references auth.users(id) on delete set null,
  action_class text not null,
  risk_class text not null default 'CAUTION' check (risk_class in ('SAFE','CAUTION','DANGEROUS','CRITICAL')),
  scope jsonb not null default '{}'::jsonb,
  max_uses integer not null default 1 check (max_uses >= 0),
  uses integer not null default 0 check (uses >= 0 and uses <= max_uses),
  max_spend_cents integer,
  status text not null default 'pending' check (status in ('pending','approved','denied','expired','revoked','consumed')),
  rationale text,
  expires_at timestamptz,
  created_at timestamptz not null default now(),
  decided_at timestamptz
);

create table if not exists pauli.runtime_providers (
  id uuid primary key default gen_random_uuid(),
  provider_key text not null unique,
  name text not null,
  kind text not null check (kind in ('agent_runtime','model','compute','integration','voice','media')),
  endpoint_ref text,
  capabilities jsonb not null default '{}'::jsonb,
  health_status text not null default 'unknown' check (health_status in ('unknown','healthy','degraded','offline','unconfigured')),
  cost_profile jsonb not null default '{}'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  last_healthcheck_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists pauli.runtime_runs (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  mission_id uuid references pauli.missions(id) on delete cascade,
  task_id uuid references pauli.mission_tasks(id) on delete set null,
  agent_id uuid references pauli.agents(id) on delete set null,
  provider_id uuid references pauli.runtime_providers(id) on delete set null,
  model_key text,
  status text not null default 'queued' check (status in ('queued','running','retrying','blocked','completed','failed','cancelled')),
  input_manifest jsonb not null default '{}'::jsonb,
  output_manifest jsonb not null default '{}'::jsonb,
  token_usage jsonb not null default '{}'::jsonb,
  cost_cents integer not null default 0,
  latency_ms integer,
  attempt integer not null default 1,
  error_class text,
  error_message text,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists pauli.compute_sessions (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  mission_id uuid references pauli.missions(id) on delete cascade,
  agent_id uuid references pauli.agents(id) on delete set null,
  provider_key text not null,
  provider_resource_id text,
  os text,
  persistent boolean not null default false,
  capabilities jsonb not null default '{}'::jsonb,
  status text not null default 'requested' check (status in ('requested','provisioning','ready','busy','sleeping','failed','destroyed')),
  estimated_cost_cents integer not null default 0,
  actual_cost_cents integer not null default 0,
  endpoint_ref text,
  snapshot_ref text,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  ended_at timestamptz
);

create table if not exists pauli.memory_entries (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  agent_id uuid references pauli.agents(id) on delete cascade,
  mission_id uuid references pauli.missions(id) on delete cascade,
  namespace text not null,
  memory_type text not null check (memory_type in ('chat_history','persona','scratchpad','execution','pattern','scaffold','anti_pattern','meta_learning','fact')),
  source_type text not null default 'system',
  source_hash text,
  content_redacted text not null,
  metadata jsonb not null default '{}'::jsonb,
  safe_for_prompt boolean not null default false,
  approved boolean not null default false,
  confidence numeric(5,4) not null default 0.50 check (confidence between 0 and 1),
  expires_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists pauli.checkpoints (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  mission_id uuid not null references pauli.missions(id) on delete cascade,
  task_id uuid references pauli.mission_tasks(id) on delete set null,
  stage_key text not null,
  reason text not null,
  state_manifest jsonb not null default '{}'::jsonb,
  state_hash text,
  storage_ref text,
  verified boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists pauli.evidence_receipts (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  mission_id uuid not null references pauli.missions(id) on delete cascade,
  task_id uuid references pauli.mission_tasks(id) on delete set null,
  runtime_run_id uuid references pauli.runtime_runs(id) on delete set null,
  status text not null default 'unverified' check (status in ('unverified','verified','rejected')),
  summary text not null,
  tests jsonb not null default '[]'::jsonb,
  artifacts jsonb not null default '[]'::jsonb,
  cost jsonb not null default '{}'::jsonb,
  verification jsonb not null default '{}'::jsonb,
  sha256 text,
  signed_at timestamptz not null default now()
);

create table if not exists pauli.integration_connections (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  actor_key text not null,
  provider text not null,
  toolkit text not null,
  external_connection_id text,
  status text not null default 'disconnected' check (status in ('disconnected','pending','connected','error','revoked')),
  permissions jsonb not null default '{}'::jsonb,
  secret_ref text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, actor_key, provider, toolkit)
);

create table if not exists pauli.world_locations (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid references pauli.organizations(id) on delete cascade,
  location_key text not null,
  name text not null,
  visibility text not null default 'tenant' check (visibility in ('public','member','tenant','team','private','system')),
  scene_ref text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (organization_id, location_key)
);

create table if not exists pauli.world_presence (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  agent_id uuid not null references pauli.agents(id) on delete cascade,
  mission_id uuid references pauli.missions(id) on delete set null,
  location_id uuid references pauli.world_locations(id) on delete set null,
  state text not null default 'idle',
  position jsonb not null default '{}'::jsonb,
  activity_summary text,
  updated_at timestamptz not null default now(),
  unique (organization_id, agent_id)
);

create table if not exists pauli.experiments (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  mission_id uuid references pauli.missions(id) on delete set null,
  hypothesis text not null,
  metric text not null,
  baseline numeric,
  target numeric,
  minimum_sample integer not null default 0,
  max_spend_cents integer not null default 1000,
  sample_size integer not null default 0,
  spend_cents integer not null default 0,
  result_value numeric,
  decision text check (decision in ('SCALE','ITERATE','HOLD','KILL')),
  decision_reason text,
  status text not null default 'active' check (status in ('draft','active','paused','completed','cancelled')),
  created_at timestamptz not null default now(),
  decided_at timestamptz
);

create table if not exists pauli.treasury_entries (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  mission_id uuid references pauli.missions(id) on delete set null,
  experiment_id uuid references pauli.experiments(id) on delete set null,
  entry_type text not null check (entry_type in ('revenue','expense','reserve','growth_allocation','refund','fee','adjustment')),
  amount_cents bigint not null,
  currency text not null default 'USD',
  source text,
  external_ref text,
  metadata jsonb not null default '{}'::jsonb,
  occurred_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create table if not exists pauli.documents (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  mission_id uuid references pauli.missions(id) on delete set null,
  category text not null,
  title text not null,
  storage_uri text not null,
  mime_type text,
  contains_sensitive_data boolean not null default false,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists pauli.audit_log (
  id bigint generated by default as identity primary key,
  organization_id uuid not null references pauli.organizations(id) on delete cascade,
  actor_user_id uuid references auth.users(id) on delete set null,
  actor_agent_id uuid references pauli.agents(id) on delete set null,
  event_type text not null,
  object_type text not null,
  object_id text,
  payload_redacted jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists pauli_missions_org_status_idx on pauli.missions(organization_id, status);
create index if not exists pauli_tasks_mission_status_idx on pauli.mission_tasks(mission_id, status);
create index if not exists pauli_events_mission_time_idx on pauli.mission_events(mission_id, occurred_at desc);
create index if not exists pauli_approvals_org_status_idx on pauli.approvals(organization_id, status);
create index if not exists pauli_runtime_runs_task_idx on pauli.runtime_runs(task_id, created_at desc);
create index if not exists pauli_memory_agent_type_idx on pauli.memory_entries(agent_id, memory_type, created_at desc);
create index if not exists pauli_evidence_mission_idx on pauli.evidence_receipts(mission_id, signed_at desc);
create index if not exists pauli_treasury_org_time_idx on pauli.treasury_entries(organization_id, occurred_at desc);

-- Private RLS helpers. Never expose these through PostgREST.
create or replace function pauli_private.is_org_member(target_org uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from pauli.memberships m
    where m.organization_id = target_org
      and m.user_id = (select auth.uid())
      and m.status = 'active'
  );
$$;

create or replace function pauli_private.has_org_role(target_org uuid, allowed_roles text[] default null)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from pauli.memberships m
    where m.organization_id = target_org
      and m.user_id = (select auth.uid())
      and m.status = 'active'
      and (allowed_roles is null or m.role = any(allowed_roles))
  );
$$;

revoke all on function pauli_private.is_org_member(uuid) from public, anon, authenticated;
revoke all on function pauli_private.has_org_role(uuid,text[]) from public, anon, authenticated;
grant usage on schema pauli_private to authenticated;
grant execute on function pauli_private.is_org_member(uuid) to authenticated;
grant execute on function pauli_private.has_org_role(uuid,text[]) to authenticated;

-- RLS on every Pauli table. Service-role/backend DB connections may bypass RLS;
-- browser/authenticated traffic must pass organization membership checks.
do $$
declare t text;
begin
  foreach t in array array[
    'organizations','memberships','agents','workflow_definitions','missions','mission_tasks',
    'mission_events','approvals','runtime_runs','compute_sessions','memory_entries','checkpoints',
    'evidence_receipts','integration_connections','world_presence','experiments','treasury_entries',
    'documents','audit_log'
  ] loop
    execute format('alter table pauli.%I enable row level security', t);
  end loop;
end $$;

alter table pauli.runtime_providers enable row level security;
alter table pauli.world_locations enable row level security;

create policy organizations_member_read on pauli.organizations
for select to authenticated using ((select pauli_private.is_org_member(id)));

create policy memberships_member_read on pauli.memberships
for select to authenticated using ((user_id = (select auth.uid())) or (select pauli_private.has_org_role(organization_id, array['owner','admin'])));

create policy memberships_admin_write on pauli.memberships
for all to authenticated
using ((select pauli_private.has_org_role(organization_id, array['owner','admin'])))
with check ((select pauli_private.has_org_role(organization_id, array['owner','admin'])));

create policy agents_member_read on pauli.agents
for select to authenticated using ((select pauli_private.is_org_member(organization_id)));
create policy agents_operator_write on pauli.agents
for all to authenticated
using ((select pauli_private.has_org_role(organization_id, array['owner','admin','operator'])))
with check ((select pauli_private.has_org_role(organization_id, array['owner','admin','operator'])));

create policy workflows_member_read on pauli.workflow_definitions
for select to authenticated using (organization_id is null or (select pauli_private.is_org_member(organization_id)));
create policy workflows_admin_write on pauli.workflow_definitions
for all to authenticated
using (organization_id is not null and (select pauli_private.has_org_role(organization_id, array['owner','admin','operator'])))
with check (organization_id is not null and (select pauli_private.has_org_role(organization_id, array['owner','admin','operator'])));

-- Operational tables share the same read/write role contract.
do $$
declare t text;
begin
  foreach t in array array[
    'missions','mission_tasks','mission_events','runtime_runs','compute_sessions','memory_entries',
    'checkpoints','evidence_receipts','integration_connections','world_presence','experiments',
    'treasury_entries','documents'
  ] loop
    execute format('create policy %I on pauli.%I for select to authenticated using ((select pauli_private.is_org_member(organization_id)))', t || '_member_read', t);
    execute format('create policy %I on pauli.%I for all to authenticated using ((select pauli_private.has_org_role(organization_id, array[''owner'',''admin'',''operator'']))) with check ((select pauli_private.has_org_role(organization_id, array[''owner'',''admin'',''operator''])))', t || '_operator_write', t);
  end loop;
end $$;

create policy approvals_member_read on pauli.approvals
for select to authenticated using ((select pauli_private.is_org_member(organization_id)));
create policy approvals_reviewer_write on pauli.approvals
for all to authenticated
using ((select pauli_private.has_org_role(organization_id, array['owner','admin','reviewer'])))
with check ((select pauli_private.has_org_role(organization_id, array['owner','admin','reviewer'])));

create policy audit_admin_read on pauli.audit_log
for select to authenticated using ((select pauli_private.has_org_role(organization_id, array['owner','admin'])));

create policy runtime_providers_member_read on pauli.runtime_providers
for select to authenticated using (exists (select 1 from pauli.memberships m where m.user_id = (select auth.uid()) and m.status = 'active'));

create policy world_locations_read on pauli.world_locations
for select to authenticated using (organization_id is null or (select pauli_private.is_org_member(organization_id)));
create policy world_locations_write on pauli.world_locations
for all to authenticated
using (organization_id is not null and (select pauli_private.has_org_role(organization_id, array['owner','admin','operator'])))
with check (organization_id is not null and (select pauli_private.has_org_role(organization_id, array['owner','admin','operator'])));

-- Browser grants are explicit. Sensitive credential material remains references only.
grant select, insert, update, delete on all tables in schema pauli to authenticated;
grant usage, select on all sequences in schema pauli to authenticated;
revoke all on all tables in schema pauli from anon;
revoke all on all sequences in schema pauli from anon;

comment on schema pauli is 'Pauli''s Place autonomous business OS control plane; tenant isolation via organization_id + RLS.';
comment on schema pauli_private is 'Private security helpers for Pauli RLS; not an API surface.';
comment on table pauli.workflow_definitions is 'Declarative multi-agent workflow definitions inspired by AgentForge Cogs; Pauli Mission Control remains authoritative.';
comment on table pauli.memory_entries is 'Namespaced agent/mission memory with safe_for_prompt and approval gates.';
comment on table pauli.evidence_receipts is 'Independent verification receipts; mission completion requires evidence, not agent self-report.';
