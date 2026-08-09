-- Pauli's Place control-plane schema for Supabase/Postgres
-- 2026-08-09
-- Canonical goals: strict tenant isolation, mission/evidence continuity,
-- approval-gated external actions, compute/runtime tracking, world observability.

create extension if not exists pgcrypto;

create table if not exists public.pauli_tenants (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  name text not null,
  preferred_language text not null default 'en' check (preferred_language in ('en','es-MX')),
  status text not null default 'active' check (status in ('active','paused','archived')),
  reserve_rate numeric(5,4) not null default 0.40,
  reinvestment_ceiling numeric(5,4) not null default 0.60,
  default_experiment_budget_cents integer not null default 1000 check (default_experiment_budget_cents >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.pauli_memberships (
  tenant_id uuid not null references public.pauli_tenants(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null default 'member' check (role in ('owner','admin','operator','viewer')),
  created_at timestamptz not null default now(),
  primary key (tenant_id, user_id)
);

create table if not exists public.pauli_agents (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.pauli_tenants(id) on delete cascade,
  agent_key text not null,
  name text not null,
  role text not null,
  specialty text,
  heart_ref text,
  soul_ref text,
  identity_ref text,
  status text not null default 'offline' check (status in ('offline','idle','working','meeting','blocked','waiting_approval','error')),
  runtime_provider text,
  model_policy jsonb not null default '{}'::jsonb,
  compute_policy jsonb not null default '{}'::jsonb,
  skill_manifest jsonb not null default '[]'::jsonb,
  memory_ref text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, agent_key)
);

create table if not exists public.pauli_missions (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.pauli_tenants(id) on delete cascade,
  created_by uuid references auth.users(id) on delete set null,
  title text not null,
  intent_original text not null,
  intent_normalized text,
  language text not null default 'en' check (language in ('en','es-MX','mixed')),
  mission_type text,
  requested_outcome text not null,
  required_completion_level text not null default 'OUTCOME_ACHIEVED',
  status text not null default 'INTENT' check (status in ('INTENT','UNDERSTOOD','PLANNED','STAFFED','PROVISIONED','EXECUTING','WAITING_APPROVAL','BLOCKED','RECOVERING','VERIFYING','DEPLOYED','OUTCOME_PENDING','OUTCOME_ACHIEVED','LEARNED','CLOSED','FAILED','CANCELLED')),
  priority integer not null default 50 check (priority between 0 and 100),
  autonomous_budget_cents integer not null default 0 check (autonomous_budget_cents >= 0),
  spent_cents integer not null default 0 check (spent_cents >= 0),
  world_location_key text,
  metadata jsonb not null default '{}'::jsonb,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.pauli_mission_events (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.pauli_tenants(id) on delete cascade,
  mission_id uuid not null references public.pauli_missions(id) on delete cascade,
  agent_id uuid references public.pauli_agents(id) on delete set null,
  event_type text not null,
  public_summary text,
  payload jsonb not null default '{}'::jsonb,
  visibility text not null default 'tenant' check (visibility in ('public','member','tenant','team','private','system')),
  created_at timestamptz not null default now()
);

create table if not exists public.pauli_tasks (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.pauli_tenants(id) on delete cascade,
  mission_id uuid not null references public.pauli_missions(id) on delete cascade,
  assigned_agent_id uuid references public.pauli_agents(id) on delete set null,
  task_key text not null,
  title text not null,
  description text,
  status text not null default 'pending' check (status in ('pending','ready','running','blocked','waiting_approval','verifying','verified','failed','cancelled')),
  depends_on uuid[] not null default '{}'::uuid[],
  acceptance_contract jsonb not null default '{}'::jsonb,
  result jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  completed_at timestamptz,
  unique (mission_id, task_key)
);

create table if not exists public.pauli_approvals (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.pauli_tenants(id) on delete cascade,
  mission_id uuid references public.pauli_missions(id) on delete cascade,
  requested_by_agent_id uuid references public.pauli_agents(id) on delete set null,
  approved_by uuid references auth.users(id) on delete set null,
  action text not null,
  scope jsonb not null default '{}'::jsonb,
  max_uses integer not null default 1 check (max_uses >= 0),
  uses integer not null default 0 check (uses >= 0),
  max_spend_cents integer,
  status text not null default 'pending' check (status in ('pending','approved','denied','expired','revoked','consumed')),
  expires_at timestamptz,
  evidence jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  decided_at timestamptz
);

create table if not exists public.pauli_compute_sessions (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.pauli_tenants(id) on delete cascade,
  mission_id uuid references public.pauli_missions(id) on delete cascade,
  agent_id uuid references public.pauli_agents(id) on delete set null,
  provider text not null,
  provider_resource_id text,
  os text,
  persistent boolean not null default false,
  capabilities jsonb not null default '{}'::jsonb,
  status text not null default 'requested' check (status in ('requested','provisioning','ready','busy','sleeping','failed','destroyed')),
  estimated_cost_cents integer not null default 0,
  actual_cost_cents integer not null default 0,
  endpoint_ref text,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  ended_at timestamptz
);

create table if not exists public.pauli_evidence (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.pauli_tenants(id) on delete cascade,
  mission_id uuid not null references public.pauli_missions(id) on delete cascade,
  task_id uuid references public.pauli_tasks(id) on delete cascade,
  evidence_type text not null,
  uri text,
  sha256 text,
  commit_sha text,
  verification_id text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.pauli_integrations (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.pauli_tenants(id) on delete cascade,
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
  unique (tenant_id, actor_key, provider, toolkit)
);

create table if not exists public.pauli_world_locations (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid references public.pauli_tenants(id) on delete cascade,
  location_key text not null,
  name text not null,
  visibility text not null default 'tenant' check (visibility in ('public','member','tenant','team','private','system')),
  scene_ref text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (tenant_id, location_key)
);

create table if not exists public.pauli_world_presence (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.pauli_tenants(id) on delete cascade,
  agent_id uuid not null references public.pauli_agents(id) on delete cascade,
  mission_id uuid references public.pauli_missions(id) on delete set null,
  location_id uuid references public.pauli_world_locations(id) on delete set null,
  state text not null default 'idle',
  position jsonb not null default '{}'::jsonb,
  activity_summary text,
  updated_at timestamptz not null default now(),
  unique (tenant_id, agent_id)
);

create table if not exists public.pauli_experiments (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.pauli_tenants(id) on delete cascade,
  mission_id uuid references public.pauli_missions(id) on delete set null,
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

create table if not exists public.pauli_treasury_entries (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.pauli_tenants(id) on delete cascade,
  mission_id uuid references public.pauli_missions(id) on delete set null,
  experiment_id uuid references public.pauli_experiments(id) on delete set null,
  entry_type text not null check (entry_type in ('revenue','expense','reserve','growth_allocation','refund','fee','adjustment')),
  amount_cents bigint not null,
  currency text not null default 'USD',
  source text,
  external_ref text,
  metadata jsonb not null default '{}'::jsonb,
  occurred_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create table if not exists public.pauli_documents (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.pauli_tenants(id) on delete cascade,
  mission_id uuid references public.pauli_missions(id) on delete set null,
  category text not null,
  title text not null,
  storage_uri text not null,
  mime_type text,
  contains_sensitive_data boolean not null default false,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists pauli_missions_tenant_status_idx on public.pauli_missions(tenant_id, status);
create index if not exists pauli_events_mission_created_idx on public.pauli_mission_events(mission_id, created_at);
create index if not exists pauli_tasks_mission_status_idx on public.pauli_tasks(mission_id, status);
create index if not exists pauli_approvals_tenant_status_idx on public.pauli_approvals(tenant_id, status);
create index if not exists pauli_evidence_mission_idx on public.pauli_evidence(mission_id, created_at);
create index if not exists pauli_treasury_tenant_time_idx on public.pauli_treasury_entries(tenant_id, occurred_at);

-- Keep security-definer helpers outside exposed schemas, per Supabase guidance.
create schema if not exists private;
revoke all on schema private from public, anon, authenticated;

create or replace function private.pauli_is_member(target_tenant uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.pauli_memberships m
    where m.tenant_id = target_tenant and m.user_id = (select auth.uid())
  );
$$;

revoke all on function private.pauli_is_member(uuid) from public, anon, authenticated;
grant usage on schema private to authenticated;
grant execute on function private.pauli_is_member(uuid) to authenticated;

alter table public.pauli_tenants enable row level security;
alter table public.pauli_memberships enable row level security;
alter table public.pauli_agents enable row level security;
alter table public.pauli_missions enable row level security;
alter table public.pauli_mission_events enable row level security;
alter table public.pauli_tasks enable row level security;
alter table public.pauli_approvals enable row level security;
alter table public.pauli_compute_sessions enable row level security;
alter table public.pauli_evidence enable row level security;
alter table public.pauli_integrations enable row level security;
alter table public.pauli_world_locations enable row level security;
alter table public.pauli_world_presence enable row level security;
alter table public.pauli_experiments enable row level security;
alter table public.pauli_treasury_entries enable row level security;
alter table public.pauli_documents enable row level security;

create policy pauli_tenants_member_select on public.pauli_tenants
for select to authenticated using ((select private.pauli_is_member(id)));

create policy pauli_memberships_member_select on public.pauli_memberships
for select to authenticated using ((select private.pauli_is_member(tenant_id)));

do $$
declare
  t text;
begin
  foreach t in array array[
    'pauli_agents','pauli_missions','pauli_mission_events','pauli_tasks','pauli_approvals',
    'pauli_compute_sessions','pauli_evidence','pauli_integrations','pauli_world_presence',
    'pauli_experiments','pauli_treasury_entries','pauli_documents'
  ]
  loop
    execute format('create policy %I on public.%I for all to authenticated using ((select private.pauli_is_member(tenant_id))) with check ((select private.pauli_is_member(tenant_id)))', t || '_tenant_access', t);
  end loop;
end $$;

create policy pauli_world_locations_read on public.pauli_world_locations
for select to authenticated using (tenant_id is null or (select private.pauli_is_member(tenant_id)));
create policy pauli_world_locations_write on public.pauli_world_locations
for all to authenticated using (tenant_id is not null and (select private.pauli_is_member(tenant_id)))
with check (tenant_id is not null and (select private.pauli_is_member(tenant_id)));

revoke all on all tables in schema public from anon;
grant select, insert, update, delete on table
  public.pauli_tenants, public.pauli_memberships, public.pauli_agents, public.pauli_missions,
  public.pauli_mission_events, public.pauli_tasks, public.pauli_approvals, public.pauli_compute_sessions,
  public.pauli_evidence, public.pauli_integrations, public.pauli_world_locations, public.pauli_world_presence,
  public.pauli_experiments, public.pauli_treasury_entries, public.pauli_documents
to authenticated;

-- No anonymous writes anywhere. Public world access, when enabled, should be exposed
-- through a narrowly scoped API/edge function that projects explicitly public data.
